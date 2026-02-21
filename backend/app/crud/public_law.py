"""CRUD operations for the Law Viewer QC tool."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_law import PublicLaw
from app.schemas.law_viewer import (
    DiffHunkSchema,
    DiffLineSchema,
    LawSummarySchema,
    LawTextSchema,
    ParsedAmendmentSchema,
    PositionQualifierSchema,
    SectionDiffSchema,
    SectionReferenceSchema,
)

logger = logging.getLogger(__name__)


async def get_laws_list(session: AsyncSession) -> list[LawSummarySchema]:
    """Return all public laws ordered by congress desc, law_number desc."""
    stmt = select(PublicLaw).order_by(
        PublicLaw.congress.desc(), PublicLaw.law_number.desc()
    )
    result = await session.execute(stmt)
    laws = result.scalars().all()

    return [
        LawSummarySchema(
            congress=law.congress,
            law_number=law.law_number,
            official_title=law.official_title,
            short_title=law.short_title,
            enacted_date=law.enacted_date.isoformat(),
            sections_affected=law.sections_affected,
        )
        for law in laws
    ]


def _date_str(d: Any) -> str | None:
    """Convert a date to ISO string, or None."""
    return d.isoformat() if d else None


async def get_law_text(
    session: AsyncSession, congress: int, law_number: int
) -> LawTextSchema | None:
    """Fetch raw HTM and XML text for a law, using cache or GovInfo API."""
    # Dynamic import to keep pipeline/ out of mypy's module graph
    try:
        govinfo_mod = importlib.import_module("pipeline.govinfo.client")
        client: Any = govinfo_mod.GovInfoClient()
    except (ValueError, ImportError):
        logger.warning("GovInfo API key not configured, reading from cache only")
        client = None

    htm_content: str | None = None
    xml_content: str | None = None

    if client:
        htm_content = await client.get_law_text(congress, law_number, format="htm")
        xml_content = await client.get_law_text(congress, law_number, format="xml")
    else:
        # Try reading from cache directly
        cache_dir = Path("data/govinfo/plaw")
        htm_file = cache_dir / f"PLAW-{congress}publ{law_number}.htm"
        xml_file = cache_dir / f"PLAW-{congress}publ{law_number}.xml"
        if htm_file.exists():
            htm_content = htm_file.read_text()
        if xml_file.exists():
            xml_content = xml_file.read_text()

    if htm_content is None and xml_content is None:
        return None

    # Query DB for metadata
    stmt = select(PublicLaw).where(
        PublicLaw.congress == congress,
        PublicLaw.law_number == str(law_number),
    )
    result = await session.execute(stmt)
    law = result.scalar_one_or_none()

    return LawTextSchema(
        congress=congress,
        law_number=str(law_number),
        official_title=law.official_title if law else None,
        short_title=law.short_title if law else None,
        enacted_date=_date_str(law.enacted_date) if law else None,
        introduced_date=_date_str(law.introduced_date) if law else None,
        house_passed_date=_date_str(law.house_passed_date) if law else None,
        senate_passed_date=_date_str(law.senate_passed_date) if law else None,
        presented_to_president_date=(
            _date_str(law.presented_to_president_date) if law else None
        ),
        effective_date=_date_str(law.effective_date) if law else None,
        htm_content=htm_content,
        xml_content=xml_content,
    )


def _amendment_to_schema(amendment: Any) -> ParsedAmendmentSchema:
    """Convert a ParsedAmendment dataclass to its API schema."""
    section_ref = None
    if amendment.section_ref:
        section_ref = SectionReferenceSchema(
            title=amendment.section_ref.title,
            section=amendment.section_ref.section,
            subsection_path=amendment.section_ref.subsection_path,
            display=str(amendment.section_ref),
        )

    position_qualifier = None
    if amendment.position_qualifier:
        position_qualifier = PositionQualifierSchema(
            type=amendment.position_qualifier.type.value,
            anchor_text=amendment.position_qualifier.anchor_text,
            target_text=amendment.position_qualifier.target_text,
        )

    return ParsedAmendmentSchema(
        pattern_name=amendment.pattern_name,
        pattern_type=amendment.pattern_type.value,
        change_type=amendment.change_type.value,
        section_ref=section_ref,
        old_text=amendment.old_text,
        new_text=amendment.new_text,
        full_match=amendment.full_match,
        confidence=amendment.confidence,
        needs_review=amendment.needs_review,
        context=amendment.context,
        position_qualifier=position_qualifier,
    )


def _find_line_number(provisions: list[dict[str, Any]], old_text: str) -> int | None:
    """Find the 1-indexed line number where old_text starts in provisions.

    Normalises whitespace for matching since amendment text and provision
    content may differ in spacing.
    """
    import re

    def normalise(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip().lower()

    needle = normalise(old_text)
    if not needle:
        return None

    # Try matching against individual lines first (most amendments touch one line)
    for line in provisions:
        content = normalise(line.get("content", ""))
        if not content:
            continue
        if needle in content or content in needle:
            return int(line.get("line_number", 1))

    # Multi-line: concatenate all provision text and find the offset
    full_text_parts: list[tuple[int, str]] = []
    for line in provisions:
        ln = int(line.get("line_number", 1))
        full_text_parts.append((ln, line.get("content", "")))

    concat = ""
    line_starts: list[tuple[int, int]] = []  # (char_offset, line_number)
    for ln, content in full_text_parts:
        line_starts.append((len(concat), ln))
        concat += content + " "

    concat_norm = normalise(concat)
    pos = concat_norm.find(needle)
    if pos == -1:
        return None

    # Map char position back to line number
    for i in range(len(line_starts) - 1, -1, -1):
        if line_starts[i][0] <= pos:
            return line_starts[i][1]
    return None


async def _get_parent_revision_id(
    session: AsyncSession, congress: int, law_number: int
) -> int | None:
    """Find the revision ID *before* this law was applied.

    Returns the parent revision of the law's revision, or HEAD as fallback.
    """
    from app.models.revision import CodeRevision
    from pipeline.olrc.snapshot_service import SnapshotService

    stmt = (
        select(CodeRevision)
        .where(CodeRevision.summary == f"PL {congress}-{law_number}")
        .limit(1)
    )
    result = await session.execute(stmt)
    law_revision = result.scalar_one_or_none()

    if law_revision and law_revision.parent_revision_id is not None:
        return law_revision.parent_revision_id

    # Fallback to HEAD if the law hasn't been applied yet
    svc = SnapshotService(session)
    return await svc.get_head_revision_id()


async def _enrich_start_lines(
    session: AsyncSession,
    schemas: list[ParsedAmendmentSchema],
    congress: int,
    law_number: int,
) -> None:
    """Look up target sections and set start_line on each amendment.

    Uses the revision *before* this law was applied so that old_text
    (the text being struck) still exists in the provisions.
    """
    from pipeline.olrc.snapshot_service import SnapshotService

    lookup_revision_id = await _get_parent_revision_id(session, congress, law_number)
    if lookup_revision_id is None:
        return

    svc = SnapshotService(session)

    # Cache provisions by (title, section) to avoid duplicate queries
    provisions_cache: dict[tuple[int, str], list[dict[str, Any]] | None] = {}

    for schema in schemas:
        if schema.old_text is None or schema.section_ref is None:
            continue
        title = schema.section_ref.title
        section = schema.section_ref.section
        if title is None:
            continue

        cache_key = (title, section)
        if cache_key not in provisions_cache:
            state = await svc.get_section_at_revision(
                title, section, lookup_revision_id
            )
            # normalized_provisions is a list stored as JSONB
            raw = state.normalized_provisions if state else None
            provisions_cache[cache_key] = raw if isinstance(raw, list) else None

        provisions = provisions_cache[cache_key]
        if provisions:
            schema.start_line = _find_line_number(provisions, schema.old_text)


async def parse_law_amendments(
    session: AsyncSession, congress: int, law_number: int
) -> list[ParsedAmendmentSchema]:
    """Parse amendments from a law's text on-the-fly for QC.

    Tries XML parsing first (higher fidelity), falls back to text parsing.
    """
    law_text = await get_law_text(session, congress, law_number)
    if not law_text:
        return []

    amendments: list[Any] = []

    # Dynamic imports to keep pipeline/ out of mypy's module graph
    if law_text.xml_content:
        try:
            xml_mod = importlib.import_module("pipeline.legal_parser.xml_parser")
            xml_parser = xml_mod.XMLAmendmentParser()
            amendments = xml_parser.parse(law_text.xml_content)
        except Exception:
            logger.exception(
                "XML parsing failed for PL %d-%d, falling back to text parser",
                congress,
                law_number,
            )
            amendments = []

    # Fall back to text parser if XML produced nothing
    if not amendments and law_text.htm_content:
        text_mod = importlib.import_module("pipeline.legal_parser.amendment_parser")
        text_parser = text_mod.AmendmentParser()
        amendments = text_parser.parse(law_text.htm_content)

    schemas = [_amendment_to_schema(a) for a in amendments]
    await _enrich_start_lines(session, schemas, congress, law_number)
    return schemas


def _provision_to_diff_line(
    prov: dict[str, Any], line_type: str = "context"
) -> DiffLineSchema:
    """Convert a provision dict to a DiffLineSchema."""
    ln = int(prov.get("line_number", 1))
    return DiffLineSchema(
        old_line_number=ln,
        new_line_number=ln,
        content=prov.get("content", ""),
        type=line_type,
        indent_level=int(prov.get("indent_level", 0)),
        marker=prov.get("marker"),
        is_header=bool(prov.get("is_header", False)),
    )


def _parse_struck_subsections(full_match: str) -> list[str] | None:
    """Extract subsection markers from a 'striking subsections (X) and (Y)' instruction.

    Returns a list of single-letter/number markers like ['a', 'b'], or None
    if the instruction doesn't match this pattern.
    """
    import re

    # Match patterns like:
    #   "striking subsections (a) and (b)"
    #   "striking subsection (a)"
    #   "striking subsections (a), (b), and (c)"
    m = re.search(
        r"striking\s+subsections?\s+((?:\([a-zA-Z0-9]+\)(?:\s*(?:,\s*|\s+and\s+))?)+)",
        full_match,
        re.IGNORECASE,
    )
    if not m:
        return None
    markers = re.findall(r"\(([a-zA-Z0-9]+)\)", m.group(1))
    return markers if markers else None


def _find_subsection_range(
    provisions: list[dict[str, Any]], markers: list[str]
) -> tuple[int, int] | None:
    """Find the contiguous index range of provision lines belonging to given subsection markers.

    Returns (start_index, end_index) inclusive, stopping at the next
    same-level marker that is NOT in the target set.  "Same-level" means
    the same marker style as the struck markers (e.g. lowercase letters).
    """
    import re

    marker_set = {f"({m})" for m in markers}

    # Determine boundary pattern from the marker style being struck.
    sample = markers[0]
    if sample.isdigit():
        boundary_re = re.compile(r"^\([0-9]+\)$")
    elif sample.isupper():
        boundary_re = re.compile(r"^\([A-Z]+\)$")
    else:
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
            if line_marker and boundary_re.match(line_marker):
                break
            end_idx = i

    if start_idx is None:
        return None
    assert end_idx is not None
    return (start_idx, end_idx)


def _apply_amendments_to_provisions(
    provisions: list[dict[str, Any]],
    amendments: list[ParsedAmendmentSchema],
) -> list[dict[str, Any]]:
    """Apply text replacements from amendments to provisions.

    Handles two cases:
    1. Simple text replacement: old_text is found in a provision line's content.
    2. Structural replacement: old_text is None but the instruction references
       subsections to strike (e.g., "striking subsections (a) and (b) and
       inserting the following"). Identifies the provision lines belonging
       to those subsections and replaces them with new_text lines.
    """
    import copy
    import re

    patched = copy.deepcopy(provisions)

    for amendment in amendments:
        if amendment.change_type not in ("Modify", "Delete"):
            continue

        # Case 1: Simple text replacement (old_text present)
        if amendment.old_text is not None:
            replacement = amendment.new_text or ""
            for line in patched:
                content = line.get("content", "")
                if not content:
                    continue

                # Exact match
                if amendment.old_text in content:
                    line["content"] = content.replace(amendment.old_text, replacement)
                    continue

                # Whitespace-normalised match
                parts = amendment.old_text.split()
                if not parts:
                    continue
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
        if amendment.new_text is None:
            continue

        struck = _parse_struck_subsections(amendment.full_match)
        if not struck:
            continue

        span = _find_subsection_range(patched, struck)
        if not span:
            continue

        start_idx, end_idx = span

        # Build replacement lines with basic marker detection.
        # Indent inference is unreliable without XML structure; the next
        # release-point ingestion will supply proper formatting.
        new_lines_text = amendment.new_text.split("\n")
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

        # Replace the struck range with new provisions
        patched[start_idx : end_idx + 1] = replacement_provisions

    # Renumber all lines sequentially so replacements that change the
    # line count don't leave gaps or duplicates.
    for i, line in enumerate(patched):
        line["line_number"] = i + 1

    return patched


def _build_hunks(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    context_lines: int = 3,
) -> list[DiffHunkSchema]:
    """Build diff hunks by comparing before/after provisions.

    Uses SequenceMatcher to handle both same-length (in-place edit) and
    different-length (structural replacement) cases.
    """
    from difflib import SequenceMatcher

    if not before and not after:
        return []

    old_contents = [p.get("content", "") for p in before]
    new_contents = [p.get("content", "") for p in after]

    sm = SequenceMatcher(None, old_contents, new_contents)
    opcodes = sm.get_opcodes()

    # Check if there are any actual changes
    if all(tag == "equal" for tag, *_ in opcodes):
        return []

    # Build a flat list of diff entries with source indices, then group into hunks
    entries: list[
        tuple[str, int | None, int | None, dict[str, Any] | None, dict[str, Any] | None]
    ] = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for k in range(i2 - i1):
                entries.append(
                    ("context", i1 + k, j1 + k, before[i1 + k], after[j1 + k])
                )
        elif tag == "replace":
            for k in range(i1, i2):
                entries.append(("removed", k, None, before[k], None))
            for k in range(j1, j2):
                entries.append(("added", None, k, None, after[k]))
        elif tag == "delete":
            for k in range(i1, i2):
                entries.append(("removed", k, None, before[k], None))
        elif tag == "insert":
            for k in range(j1, j2):
                entries.append(("added", None, k, None, after[k]))

    # Mark which entries are changes (not context)
    is_change = [e[0] != "context" for e in entries]

    # Expand change regions by context_lines and merge overlapping ranges
    n = len(entries)
    in_hunk = [False] * n
    for i, changed in enumerate(is_change):
        if changed:
            for j in range(max(0, i - context_lines), min(n, i + context_lines + 1)):
                in_hunk[j] = True

    # Split into contiguous hunk regions
    hunk_ranges: list[tuple[int, int]] = []
    start: int | None = None
    for i in range(n):
        if in_hunk[i]:
            if start is None:
                start = i
        else:
            if start is not None:
                hunk_ranges.append((start, i - 1))
                start = None
    if start is not None:
        hunk_ranges.append((start, n - 1))

    hunks: list[DiffHunkSchema] = []
    for h_start, h_end in hunk_ranges:
        lines: list[DiffLineSchema] = []
        first_old_ln = 1
        first_new_ln = 1

        for i in range(h_start, h_end + 1):
            line_type, old_idx, new_idx, old_prov, new_prov = entries[i]

            if line_type == "context":
                assert old_prov is not None and new_prov is not None
                old_ln = int(old_prov.get("line_number", (old_idx or 0) + 1))
                new_ln = int(new_prov.get("line_number", (new_idx or 0) + 1))
                if i == h_start:
                    first_old_ln = old_ln
                    first_new_ln = new_ln
                lines.append(
                    DiffLineSchema(
                        old_line_number=old_ln,
                        new_line_number=new_ln,
                        content=old_prov.get("content", ""),
                        type="context",
                        indent_level=int(old_prov.get("indent_level", 0)),
                        marker=old_prov.get("marker"),
                        is_header=bool(old_prov.get("is_header", False)),
                    )
                )
            elif line_type == "removed":
                assert old_prov is not None
                old_ln = int(old_prov.get("line_number", (old_idx or 0) + 1))
                if i == h_start:
                    first_old_ln = old_ln
                lines.append(
                    DiffLineSchema(
                        old_line_number=old_ln,
                        new_line_number=None,
                        content=old_prov.get("content", ""),
                        type="removed",
                        indent_level=int(old_prov.get("indent_level", 0)),
                        marker=old_prov.get("marker"),
                        is_header=bool(old_prov.get("is_header", False)),
                    )
                )
            elif line_type == "added":
                assert new_prov is not None
                new_ln = int(new_prov.get("line_number", (new_idx or 0) + 1))
                if i == h_start:
                    first_new_ln = new_ln
                lines.append(
                    DiffLineSchema(
                        old_line_number=None,
                        new_line_number=new_ln,
                        content=new_prov.get("content", ""),
                        type="added",
                        indent_level=int(new_prov.get("indent_level", 0)),
                        marker=new_prov.get("marker"),
                        is_header=bool(new_prov.get("is_header", False)),
                    )
                )

        hunks.append(
            DiffHunkSchema(old_start=first_old_ln, new_start=first_new_ln, lines=lines)
        )

    return hunks


async def compute_law_diffs(
    session: AsyncSession, congress: int, law_number: int
) -> list[SectionDiffSchema]:
    """Compute per-section unified diffs for a law's amendments.

    Groups amendments by (title, section), fetches before provisions,
    applies amendments to get after provisions, and builds diff hunks.
    """
    from pipeline.olrc.snapshot_service import SnapshotService

    # Parse amendments (reuses existing logic)
    schemas = await parse_law_amendments(session, congress, law_number)
    if not schemas:
        return []

    # Get parent revision for "before" state
    revision_id = await _get_parent_revision_id(session, congress, law_number)
    if revision_id is None:
        return []

    # Group amendments by (title, section)
    groups: dict[tuple[int, str], list[ParsedAmendmentSchema]] = {}
    for s in schemas:
        if s.section_ref is None or s.section_ref.title is None:
            continue
        key = (s.section_ref.title, s.section_ref.section)
        groups.setdefault(key, []).append(s)

    svc = SnapshotService(session)
    diffs: list[SectionDiffSchema] = []

    for (title, section), section_amendments in groups.items():
        # Fetch "before" provisions
        state = await svc.get_section_at_revision(title, section, revision_id)
        raw = state.normalized_provisions if state else None
        if not isinstance(raw, list) or not raw:
            # No provisions — emit a diff with just amendments metadata
            diffs.append(
                SectionDiffSchema(
                    title_number=title,
                    section_number=section,
                    section_key=f"{title} U.S.C. § {section}",
                    heading=state.heading if state else "",
                    hunks=[],
                    total_lines=0,
                    amendments=section_amendments,
                    all_provisions=[],
                )
            )
            continue

        before = raw
        after = _apply_amendments_to_provisions(before, section_amendments)
        hunks = _build_hunks(before, after)

        # Build all_provisions from "after" state for expansion
        all_provisions = [_provision_to_diff_line(p) for p in after]

        diffs.append(
            SectionDiffSchema(
                title_number=title,
                section_number=section,
                section_key=f"{title} U.S.C. § {section}",
                heading=state.heading if state else "",
                hunks=hunks,
                total_lines=len(after),
                amendments=section_amendments,
                all_provisions=all_provisions,
            )
        )

    return diffs
