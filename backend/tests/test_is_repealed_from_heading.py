"""Unit tests for is_repealed detection from section heading text.

The section_snapshot table has an is_deleted column (tracks removal during a
revision) but no is_repealed column.  Sections marked status="repealed" in the
OLRC XML always have a heading that starts with "Repealed." — this is the
canonical OLRC convention.  The CRUD layer therefore derives is_repealed as:

    is_deleted OR heading.startswith("Repealed.")

Regression coverage for issue #707: before the fix, is_repealed was wired to
state.is_deleted only, which is always False for a section that still exists in
the snapshot (it was not *deleted* from the revision, just repealed in statute).
"""

import uuid

from app.crud.us_code import _build_section_summary
from pipeline.olrc.snapshot_service import SectionState


def _make_state(
    heading: str | None,
    is_deleted: bool = False,
) -> SectionState:
    """Construct a minimal SectionState for testing is_repealed detection."""
    return SectionState(
        title_number=37,
        section_number="904",
        heading=heading,
        text_content=None,
        text_hash=None,
        normalized_provisions=None,
        notes=None,
        normalized_notes=None,
        notes_hash=None,
        full_citation=None,
        snapshot_id=1,
        revision_id=1,
        is_deleted=is_deleted,
        group_id=uuid.uuid4(),
        sort_order=0,
    )


class TestIsRepealedFromHeading:
    """is_repealed is True when the heading starts with 'Repealed.'."""

    def test_repealed_heading_sets_is_repealed_true(self) -> None:
        """Regression for issue #707: heading 'Repealed. Pub. L. ...' yields is_repealed=True.

        The OLRC uses this exact prefix for all repealed sections; the old code
        returned False because it only checked is_deleted.
        """
        state = _make_state(
            "Repealed. Pub. L. 96–513, title IV, § 403(a), Dec. 12, 1980, 94 Stat. 2904"
        )
        summary = _build_section_summary(state)
        assert summary.is_repealed is True

    def test_bare_repealed_prefix_sets_is_repealed_true(self) -> None:
        """Even a heading that is exactly 'Repealed.' triggers the flag."""
        state = _make_state("Repealed.")
        summary = _build_section_summary(state)
        assert summary.is_repealed is True

    def test_normal_heading_leaves_is_repealed_false(self) -> None:
        """A section with a normal heading and is_deleted=False is not repealed."""
        state = _make_state("Definitions")
        summary = _build_section_summary(state)
        assert summary.is_repealed is False

    def test_is_deleted_alone_sets_is_repealed_true(self) -> None:
        """is_deleted=True (section removed in a revision) still marks repealed."""
        state = _make_state("Some section", is_deleted=True)
        summary = _build_section_summary(state)
        assert summary.is_repealed is True

    def test_heading_containing_repealed_not_at_start_is_false(self) -> None:
        """A heading that contains 'Repealed' mid-string does not trigger the flag."""
        state = _make_state("Transfer of Repealed Provisions")
        summary = _build_section_summary(state)
        assert summary.is_repealed is False

    def test_none_heading_is_not_repealed(self) -> None:
        """A None heading does not raise and returns is_repealed=False."""
        state = _make_state(None)
        summary = _build_section_summary(state)
        assert summary.is_repealed is False

    def test_repealed_heading_case_sensitive(self) -> None:
        """The check is case-sensitive: lowercase 'repealed.' is not matched."""
        state = _make_state("repealed. pub. l. 96-513")
        summary = _build_section_summary(state)
        assert summary.is_repealed is False
