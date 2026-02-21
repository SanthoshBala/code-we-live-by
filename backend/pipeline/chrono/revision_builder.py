"""Orchestrator for building derived CodeRevisions from law changes.

Creates a CodeRevision (type=PUBLIC_LAW) by applying all LawChange records
for a given PublicLaw to the parent revision's section state.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ChangeType, RevisionStatus, RevisionType
from app.models.public_law import LawChange, PublicLaw
from app.models.revision import CodeRevision
from app.models.snapshot import SectionSnapshot
from pipeline.chrono.amendment_applicator import (
    ApplicationResult,
    ApplicationStatus,
    apply_text_change,
)
from pipeline.chrono.notes_updater import update_notes_for_applied_law
from pipeline.olrc.parser import compute_text_hash
from pipeline.olrc.snapshot_service import SnapshotService

logger = logging.getLogger(__name__)


def _parse_redesignation(text: str) -> list[tuple[int, str]] | None:
    """Extract ordinal→marker pairs from a redesignation instruction.

    E.g. "designating the first, second, and third sentences as subsections
    (a), (c), and (d)" → [(0, "(a)"), (1, "(c)"), (2, "(d)")].

    Returns None if the text doesn't match a redesignation pattern.
    """
    import re

    ORDINALS = {
        "first": 0,
        "second": 1,
        "third": 2,
        "fourth": 3,
        "fifth": 4,
        "sixth": 5,
        "seventh": 6,
        "eighth": 7,
        "ninth": 8,
        "tenth": 9,
    }

    m = re.search(
        r"designating\s+the\s+((?:(?:first|second|third|fourth|fifth|sixth|"
        r"seventh|eighth|ninth|tenth)(?:\s*,\s+and\s+|\s*,\s*|\s+and\s+|\s*))+)"
        r"sentences?\s+as\s+subsections?\s+"
        r"((?:\([a-zA-Z0-9]+\)(?:\s*,\s+and\s+|\s*,\s*|\s+and\s+|\s*))+)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None

    ordinal_words = re.findall(
        r"(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)",
        m.group(1),
        re.IGNORECASE,
    )
    markers = re.findall(r"(\([a-zA-Z0-9]+\))", m.group(2))

    if len(ordinal_words) != len(markers):
        return None

    result: list[tuple[int, str]] = []
    for word, marker in zip(ordinal_words, markers, strict=False):
        idx = ORDINALS.get(word.lower())
        if idx is None:
            return None
        result.append((idx, marker))

    return result if result else None


def _parse_struck_subsections(text: str) -> list[str] | None:
    """Extract subsection markers from a 'striking subsections (X) and (Y)' instruction.

    Returns a list of single-letter/number markers like ['a', 'b'], or None
    if the instruction doesn't match this pattern.
    """
    import re

    m = re.search(
        r"striking\s+subsections?\s+"
        r"((?:\([a-zA-Z0-9]+\)(?:\s*(?:,\s*|\s+and\s+))?)+)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    markers = re.findall(r"\(([a-zA-Z0-9]+)\)", m.group(1))
    return markers if markers else None


def _find_subsection_range(
    provisions: list[dict[str, Any]], markers: list[str]
) -> tuple[int, int] | None:
    """Find the contiguous index range of provision lines belonging to
    the given subsection markers.

    Returns (start_index, end_index) inclusive, stopping at the next
    top-level subsection that is NOT in the target set.

    "Top-level" means the same marker style as the struck markers.
    E.g. if striking (a) and (b) (lowercase letters), then (c) is a
    boundary but (1), (A), (i) are children and should be included.
    """
    import re

    marker_set = {f"({m})" for m in markers}

    # Determine what kind of markers we're striking to know what
    # constitutes a same-level boundary.  E.g. lowercase letters →
    # only other lowercase-letter markers are boundaries.
    sample = markers[0]
    if sample.isdigit():
        boundary_re = re.compile(r"^\([0-9]+\)$")
    elif sample.isupper():
        boundary_re = re.compile(r"^\([A-Z]+\)$")
    else:
        # lowercase letters (most common: subsections (a), (b), …)
        boundary_re = re.compile(r"^\([a-z]+\)$")

    start_idx: int | None = None
    end_idx: int | None = None

    for i, line in enumerate(provisions):
        line_marker = line.get("marker", "")
        if line_marker in marker_set:
            if start_idx is None:
                start_idx = i
            end_idx = i
        elif start_idx is not None:
            # Stop at the next same-level marker outside the target set
            if line_marker and boundary_re.match(line_marker):
                break
            end_idx = i

    if start_idx is None:
        return None
    assert end_idx is not None
    return (start_idx, end_idx)


def _prev_marker(marker: str) -> str | None:
    """Return the marker that logically precedes *marker*.

    E.g. "b" → "a", "3" → "2", "B" → "A".  Returns None for the
    first in sequence ("a", "1", "A").
    """
    if marker.isdigit():
        val = int(marker)
        return str(val - 1) if val > 1 else None
    if len(marker) == 1 and marker.isalpha():
        prev_ord = ord(marker) - 1
        if marker.islower() and prev_ord >= ord("a"):
            return chr(prev_ord)
        if marker.isupper() and prev_ord >= ord("A"):
            return chr(prev_ord)
    return None


def _patch_provisions(
    parent_provisions: Any,
    changes: list[LawChange],
) -> Any:
    """Apply text replacements to provision lines, preserving structure.

    Handles two cases:
    1. Simple text replacement: old_text is found in a provision line's content.
    2. Structural replacement: old_text is None but the description references
       subsections to strike (e.g., "striking subsections (a) and (b) and
       inserting the following"). Identifies the provision lines belonging
       to those subsections and replaces them with new_text lines.

    Returns a new list (or None if the parent had no provisions).
    """
    if not isinstance(parent_provisions, list):
        return parent_provisions

    import copy
    import re

    patched = copy.deepcopy(parent_provisions)

    # Process redesignations first so markers exist for subsequent ADD anchoring
    for change in changes:
        if change.change_type != ChangeType.REDESIGNATE:
            continue
        instruction = change.description or ""
        mapping = _parse_redesignation(instruction)
        if not mapping:
            continue
        for idx, new_marker in mapping:
            if 0 <= idx < len(patched):
                patched[idx]["marker"] = new_marker
                content = patched[idx].get("content", "")
                # Prepend marker to content if not already present
                if not content.startswith(new_marker):
                    patched[idx]["content"] = f"{new_marker} {content}"

    for change in changes:
        if change.change_type not in (
            ChangeType.MODIFY,
            ChangeType.DELETE,
            ChangeType.ADD,
        ):
            continue

        # Case 3: ADD — insert new provisions at the correct position
        if change.change_type == ChangeType.ADD and change.new_text:
            new_lines_text = change.new_text.split("\n")
            insert_idx = len(patched)  # default: append at end

            # Infer insertion point from new_text marker (e.g. "(b)" → after "(a)")
            first_line = new_lines_text[0].strip()
            marker_match = re.match(r"^\(([a-zA-Z0-9]+)\)", first_line)
            if marker_match:
                marker_val = marker_match.group(1)
                prev = _prev_marker(marker_val)
                if prev:
                    span = _find_subsection_range(patched, [prev])
                    if span:
                        insert_idx = span[1] + 1

            # Build provision dicts
            base_line_number = (
                int(patched[insert_idx - 1].get("line_number", insert_idx)) + 1
                if insert_idx > 0 and patched
                else 1
            )
            base_char = (
                int(patched[insert_idx - 1].get("end_char", 0))
                if insert_idx > 0 and patched
                else 0
            )
            char_offset = base_char
            line_num = base_line_number
            new_provisions: list[dict[str, Any]] = []
            for text in new_lines_text:
                text = text.strip()
                if not text:
                    continue
                m_marker = re.match(r"^(\([a-zA-Z0-9]+\)(?:\([A-Z0-9]+\))?)", text)
                marker = m_marker.group(1) if m_marker else None
                new_provisions.append(
                    {
                        "line_number": line_num,
                        "content": text,
                        "indent_level": 0,
                        "marker": marker,
                        "is_header": False,
                        "start_char": char_offset,
                        "end_char": char_offset + len(text),
                    }
                )
                line_num += 1
                char_offset += len(text) + 1

            patched[insert_idx:insert_idx] = new_provisions
            continue

        # Case 1: Simple text replacement (old_text present)
        if change.old_text is not None:
            replacement = change.new_text or ""
            for line in patched:
                content = line.get("content", "")
                if not content:
                    continue

                # Exact match
                if change.old_text in content:
                    line["content"] = content.replace(change.old_text, replacement)
                    continue

                # Whitespace-normalised match
                parts = change.old_text.split()
                ws_pattern = r"\s+".join(re.escape(part) for part in parts)
                ws_re = re.compile(ws_pattern)
                match = ws_re.search(content)
                if match:
                    line["content"] = (
                        content[: match.start()] + replacement + content[match.end() :]
                    )
                    continue

                # Case-insensitive fallback
                ci_re = re.compile(ws_pattern, re.IGNORECASE)
                match = ci_re.search(content)
                if match:
                    line["content"] = (
                        content[: match.start()] + replacement + content[match.end() :]
                    )
            continue

        # Case 2: Structural replacement (old_text is None, new_text present)
        if change.new_text is None:
            continue

        # Parse the instruction from description to find struck subsections
        instruction = change.description or ""
        struck = _parse_struck_subsections(instruction)
        if not struck:
            continue

        span = _find_subsection_range(patched, struck)
        if not span:
            continue

        start_idx, end_idx = span

        # Build replacement lines from new_text with basic marker
        # detection.  We don't attempt indent inference here because
        # heuristic-based nesting is unreliable without XML structure;
        # the next release-point ingestion will supply proper formatting.
        new_lines_text = change.new_text.split("\n")
        base_line_number = int(patched[start_idx].get("line_number", start_idx + 1))
        base_char = int(patched[start_idx].get("start_char", 0))
        char_offset = base_char
        line_num = base_line_number
        replacement_provisions: list[dict[str, Any]] = []
        for text in new_lines_text:
            text = text.strip()
            if not text:
                continue
            marker_match = re.match(r"^(\([a-zA-Z0-9]+\)(?:\([A-Z0-9]+\))?)", text)
            marker = marker_match.group(1) if marker_match else None
            replacement_provisions.append(
                {
                    "line_number": line_num,
                    "content": text,
                    "indent_level": 0,
                    "marker": marker,
                    "is_header": False,
                    "start_char": char_offset,
                    "end_char": char_offset + len(text),
                }
            )
            line_num += 1
            char_offset += len(text) + 1

        patched[start_idx : end_idx + 1] = replacement_provisions

    # Renumber all lines sequentially so replacements that change the
    # line count don't leave gaps or duplicates.
    for i, line in enumerate(patched):
        line["line_number"] = i + 1

    return patched


@dataclass
class RevisionBuildResult:
    """Summary of a revision build operation."""

    revision_id: int
    law_id: int
    parent_revision_id: int
    sequence_number: int
    sections_applied: int = 0
    sections_skipped: int = 0
    sections_failed: int = 0
    sections_added: int = 0
    sections_repealed: int = 0
    application_results: list[ApplicationResult] = field(default_factory=list)
    elapsed_seconds: float = 0.0


class RevisionBuilder:
    """Builds derived revisions by applying law changes."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.snapshot_service = SnapshotService(session)

    async def build_revision(
        self,
        law: PublicLaw,
        parent_revision_id: int,
        sequence_number: int,
    ) -> RevisionBuildResult:
        """Build a CodeRevision by applying all LawChange records for a law.

        Args:
            law: The PublicLaw whose changes to apply.
            parent_revision_id: ID of the parent revision.
            sequence_number: Global ordering position for the new revision.

        Returns:
            RevisionBuildResult with counts and details.
        """
        start = time.monotonic()

        # 1. Idempotency: check if revision already exists for this law
        existing_stmt = select(CodeRevision).where(
            CodeRevision.law_id == law.law_id,
            CodeRevision.status == RevisionStatus.INGESTED.value,
        )
        existing_result = await self.session.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            logger.info(
                "Revision already exists for PL %s-%s (revision_id=%d)",
                law.congress,
                law.law_number,
                existing.revision_id,
            )
            return RevisionBuildResult(
                revision_id=existing.revision_id,
                law_id=law.law_id,
                parent_revision_id=parent_revision_id,
                sequence_number=existing.sequence_number,
                elapsed_seconds=time.monotonic() - start,
            )

        # 2. Fetch LawChange records
        changes_stmt = (
            select(LawChange)
            .where(LawChange.law_id == law.law_id)
            .order_by(LawChange.change_id)
        )
        changes_result = await self.session.execute(changes_stmt)
        changes = list(changes_result.scalars().all())

        if not changes:
            logger.warning(
                "No LawChange records for PL %s-%s", law.congress, law.law_number
            )

        # 3. Create CodeRevision
        revision = CodeRevision(
            revision_type=RevisionType.PUBLIC_LAW.value,
            law_id=law.law_id,
            parent_revision_id=parent_revision_id,
            effective_date=law.enacted_date,
            is_ground_truth=False,
            status=RevisionStatus.INGESTING.value,
            sequence_number=sequence_number,
            summary=f"PL {law.congress}-{law.law_number}",
        )
        self.session.add(revision)
        await self.session.flush()  # Get revision_id

        result = RevisionBuildResult(
            revision_id=revision.revision_id,
            law_id=law.law_id,
            parent_revision_id=parent_revision_id,
            sequence_number=sequence_number,
        )

        # 4. Group changes by (title_number, section_number)
        section_groups: dict[tuple[int, str], list[LawChange]] = {}
        for change in changes:
            key = (change.title_number, change.section_number)
            section_groups.setdefault(key, []).append(change)

        # 5. Process each section group
        for (title_num, section_num), section_changes in section_groups.items():
            await self._apply_section_changes(
                revision=revision,
                title_number=title_num,
                section_number=section_num,
                section_changes=section_changes,
                parent_revision_id=parent_revision_id,
                law=law,
                result=result,
            )

        # 6. Mark revision as INGESTED
        revision.status = RevisionStatus.INGESTED.value
        await self.session.flush()

        result.elapsed_seconds = time.monotonic() - start
        logger.info(
            "Built revision %d for PL %s-%s: "
            "%d applied, %d skipped, %d failed, %d added, %d repealed",
            revision.revision_id,
            law.congress,
            law.law_number,
            result.sections_applied,
            result.sections_skipped,
            result.sections_failed,
            result.sections_added,
            result.sections_repealed,
        )
        return result

    async def _apply_section_changes(
        self,
        revision: CodeRevision,
        title_number: int,
        section_number: str,
        section_changes: list[LawChange],
        parent_revision_id: int,
        law: PublicLaw,
        result: RevisionBuildResult,
    ) -> None:
        """Apply all changes for a single section and create a snapshot."""
        # Fetch parent state
        parent_state = await self.snapshot_service.get_section_at_revision(
            title_number, section_number, parent_revision_id
        )

        current_text = parent_state.text_content if parent_state else None
        is_deleted = False
        is_new_section = parent_state is None
        any_applied = False
        descriptions: list[str] = []

        has_structural_changes = False

        for change in section_changes:
            app_result = apply_text_change(
                text_content=current_text,
                change_type=change.change_type,
                old_text=change.old_text,
                new_text=change.new_text,
                title_number=title_number,
                section_number=section_number,
            )
            result.application_results.append(app_result)

            if app_result.status == ApplicationStatus.APPLIED:
                any_applied = True
                current_text = app_result.new_text
                desc = change.description or app_result.description
                descriptions.append(desc)

                if change.change_type == ChangeType.REPEAL:
                    is_deleted = True
                    result.sections_repealed += 1
                    break  # No further changes after repeal
                elif change.change_type == ChangeType.ADD and is_new_section:
                    result.sections_added += 1
                    is_new_section = False  # Only count once
                else:
                    result.sections_applied += 1

            elif app_result.status == ApplicationStatus.SKIPPED:
                # Redesignations are SKIPPED by apply_text_change (no
                # old/new text), but _patch_provisions handles them at
                # the provision-line level.  Mark as applied so a
                # snapshot is still created.
                if change.change_type == ChangeType.REDESIGNATE:
                    any_applied = True
                    has_structural_changes = True
                    desc = change.description or app_result.description
                    descriptions.append(desc)
                    result.sections_applied += 1
                elif change.change_type == ChangeType.ADD_NOTE:
                    any_applied = True
                    desc = change.description or "Added statutory note"
                    descriptions.append(desc)
                    result.sections_applied += 1
                else:
                    result.sections_skipped += 1

            elif app_result.status == ApplicationStatus.FAILED:
                # Structural amendments (MODIFY with old_text=None) and ADD
                # insertions into existing sections can't be applied at the
                # text level, but _patch_provisions handles them at the
                # provision-line level.  Mark as applied so a snapshot is
                # still created.
                is_structural_modify = (
                    change.change_type == ChangeType.MODIFY
                    and change.old_text is None
                    and change.new_text is not None
                )
                is_add_to_existing = (
                    change.change_type == ChangeType.ADD
                    and change.new_text is not None
                    and not is_new_section
                )
                if is_structural_modify or is_add_to_existing:
                    any_applied = True
                    has_structural_changes = True
                    desc = change.description or app_result.description
                    descriptions.append(desc)
                    result.sections_applied += 1
                else:
                    result.sections_failed += 1
                    logger.warning(
                        "Failed to apply %s change to %d USC %s: %s",
                        change.change_type.value,
                        title_number,
                        section_number,
                        app_result.description,
                    )

        # Only create a snapshot if something changed
        if not any_applied:
            return

        # Update notes
        existing_notes = parent_state.normalized_notes if parent_state else None
        existing_raw_notes = parent_state.notes if parent_state else None
        combined_description = "; ".join(descriptions)
        updated_notes_dict, updated_raw_notes = update_notes_for_applied_law(
            existing_notes=existing_notes,
            raw_notes=existing_raw_notes,
            law=law,
            change_type=section_changes[0].change_type,
            description=combined_description,
        )

        # Compute hashes
        text_hash = compute_text_hash(current_text) if current_text else None
        notes_hash = compute_text_hash(updated_raw_notes) if updated_raw_notes else None

        # Patch provisions in-place: apply the same text replacements to
        # each provision line's content.  This preserves the original
        # structure (headers, markers, indentation) from the parent
        # snapshot while keeping content in sync with text_content.
        provisions_json = _patch_provisions(
            parent_state.normalized_provisions if parent_state else None,
            section_changes,
        )

        # For structural amendments, rebuild text_content from patched
        # provisions since apply_text_change couldn't handle them.
        if has_structural_changes and isinstance(provisions_json, list):
            current_text = "\n".join(
                line.get("content", "") for line in provisions_json
            )

        # Create snapshot, carrying forward structural metadata from parent
        snapshot = SectionSnapshot(
            revision_id=revision.revision_id,
            title_number=title_number,
            section_number=section_number,
            heading=parent_state.heading if parent_state else None,
            text_content=current_text,
            normalized_provisions=provisions_json,
            notes=updated_raw_notes,
            normalized_notes=updated_notes_dict,
            text_hash=text_hash,
            notes_hash=notes_hash,
            full_citation=(
                parent_state.full_citation
                if parent_state
                else f"{title_number} USC {section_number}"
            ),
            is_deleted=is_deleted,
            group_id=parent_state.group_id if parent_state else None,
            sort_order=parent_state.sort_order if parent_state else 0,
        )
        self.session.add(snapshot)
