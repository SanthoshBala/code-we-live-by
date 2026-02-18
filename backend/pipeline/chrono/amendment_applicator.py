"""Pure text transforms for applying law changes to section content.

No database access. All state is passed in and returned.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import StrEnum

from app.models.enums import ChangeType

logger = logging.getLogger(__name__)


class ApplicationStatus(StrEnum):
    """Result status of applying a single law change."""

    APPLIED = "applied"
    SKIPPED = "skipped"  # REDESIGNATE/TRANSFER — structural, logged only
    FAILED = "failed"  # old_text not found
    NO_CHANGE = "no_change"  # text already matches target


@dataclass
class ApplicationResult:
    """Result of applying a single text change."""

    status: ApplicationStatus
    new_text: str | None
    change_type: ChangeType
    title_number: int
    section_number: str
    description: str
    old_text_matched: bool


def _normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace into single spaces."""
    return re.sub(r"\s+", " ", text.strip())


def _find_and_replace(
    text_content: str,
    old_text: str,
    new_text: str | None,
) -> tuple[str | None, bool]:
    """Find old_text in text_content and replace with new_text.

    Tries exact match first, then whitespace-normalized, then case-insensitive.
    Replaces only the first occurrence.

    Returns:
        (result_text, matched) — result_text is None if not found.
    """
    replacement = new_text if new_text is not None else ""

    # 1. Exact match
    if old_text in text_content:
        return text_content.replace(old_text, replacement, 1), True

    # 2. Whitespace-normalized match
    norm_old = _normalize_whitespace(old_text)
    norm_content = _normalize_whitespace(text_content)
    if norm_old in norm_content:
        # Build a whitespace-flexible pattern from old_text
        parts = old_text.split()
        ws_pattern = r"\s+".join(re.escape(part) for part in parts)
        ws_re = re.compile(ws_pattern)
        match = ws_re.search(text_content)
        if match:
            result = (
                text_content[: match.start()]
                + replacement
                + text_content[match.end() :]
            )
            return result, True

    # 3. Case-insensitive match (last resort)
    parts = old_text.split()
    ws_pattern = r"\s+".join(re.escape(part) for part in parts)
    ci_re = re.compile(ws_pattern, re.IGNORECASE)
    match = ci_re.search(text_content)
    if match:
        logger.warning(
            "Case-insensitive fallback used for text match "
            "(original: %r, found: %r)",
            old_text[:80],
            match.group()[:80],
        )
        result = (
            text_content[: match.start()] + replacement + text_content[match.end() :]
        )
        return result, True

    return None, False


def apply_text_change(
    text_content: str | None,
    change_type: ChangeType,
    old_text: str | None,
    new_text: str | None,
    title_number: int,
    section_number: str,
) -> ApplicationResult:
    """Apply a single law change to section text content.

    Dispatches by change_type:
    - MODIFY: find old_text, replace with new_text
    - DELETE: find old_text, remove it
    - ADD: append new_text (or create section if content is None)
    - REPEAL: return None text (caller sets is_deleted)
    - REDESIGNATE/TRANSFER: return SKIPPED

    Args:
        text_content: Current section text (None for new sections).
        change_type: Type of change to apply.
        old_text: Text to find/replace (for MODIFY/DELETE).
        new_text: Replacement or new text.
        title_number: US Code title number.
        section_number: Section number string.

    Returns:
        ApplicationResult with status and updated text.
    """
    description = f"{change_type.value} on {title_number} USC {section_number}"

    # Structural changes — skip
    if change_type in (ChangeType.REDESIGNATE, ChangeType.TRANSFER):
        return ApplicationResult(
            status=ApplicationStatus.SKIPPED,
            new_text=text_content,
            change_type=change_type,
            title_number=title_number,
            section_number=section_number,
            description=description,
            old_text_matched=False,
        )

    # REPEAL — mark section as deleted
    if change_type == ChangeType.REPEAL:
        return ApplicationResult(
            status=ApplicationStatus.APPLIED,
            new_text=None,
            change_type=change_type,
            title_number=title_number,
            section_number=section_number,
            description=description,
            old_text_matched=True,
        )

    # ADD — append or create
    if change_type == ChangeType.ADD:
        if text_content is None:
            result_text = new_text or ""
        else:
            result_text = text_content + (new_text or "")
        return ApplicationResult(
            status=ApplicationStatus.APPLIED,
            new_text=result_text,
            change_type=change_type,
            title_number=title_number,
            section_number=section_number,
            description=description,
            old_text_matched=True,
        )

    # MODIFY / DELETE — need to find old_text in content
    if text_content is None or old_text is None:
        return ApplicationResult(
            status=ApplicationStatus.FAILED,
            new_text=text_content,
            change_type=change_type,
            title_number=title_number,
            section_number=section_number,
            description=f"{description}: no text content or old_text",
            old_text_matched=False,
        )

    replace_with = new_text if change_type == ChangeType.MODIFY else None
    result_text, matched = _find_and_replace(text_content, old_text, replace_with)

    if not matched:
        return ApplicationResult(
            status=ApplicationStatus.FAILED,
            new_text=text_content,
            change_type=change_type,
            title_number=title_number,
            section_number=section_number,
            description=f"{description}: old_text not found",
            old_text_matched=False,
        )

    return ApplicationResult(
        status=ApplicationStatus.APPLIED,
        new_text=result_text,
        change_type=change_type,
        title_number=title_number,
        section_number=section_number,
        description=description,
        old_text_matched=True,
    )
