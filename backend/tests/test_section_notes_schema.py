"""Tests for SectionNotesSchema — specifically the raw_notes markup-stripping validator."""

import pytest

from app.schemas.us_code import SectionNotesSchema


class TestRawNotesMarkupStripping:
    """raw_notes should have internal XML markup tokens stripped before API exposure."""

    def _make_notes(self, raw_notes: str) -> SectionNotesSchema:
        return SectionNotesSchema.model_validate({"raw_notes": raw_notes})

    def test_qc_markers_stripped_text_kept(self) -> None:
        raw = 'provided that: [QC:1]"The amendments shall apply."[/QC] No Requirement'
        result = self._make_notes(raw)
        assert "[QC:1]" not in result.raw_notes
        assert "[/QC]" not in result.raw_notes
        assert "amendments shall apply" in result.raw_notes
        assert "No Requirement" in result.raw_notes

    def test_qc_multilevel_stripped(self) -> None:
        raw = "[QC:1]Level one.[/QC] text [QC:3]Level three.[/QC]"
        result = self._make_notes(raw)
        assert "[QC:" not in result.raw_notes
        assert "Level one." in result.raw_notes
        assert "Level three." in result.raw_notes

    def test_h2_markers_stripped_text_kept(self) -> None:
        raw = "provided that: [H2]Brevity[/H2] (i) Poetry: ..."
        result = self._make_notes(raw)
        assert "[H2]" not in result.raw_notes
        assert "[/H2]" not in result.raw_notes
        assert "Brevity" in result.raw_notes
        assert "Poetry" in result.raw_notes

    def test_h1_markers_stripped_text_removed(self) -> None:
        raw = "Content. [H1]Cross-Heading[/H1] More content."
        result = self._make_notes(raw)
        assert "[H1]" not in result.raw_notes
        assert "Cross-Heading" not in result.raw_notes
        assert "More content." in result.raw_notes

    def test_plain_text_unchanged(self) -> None:
        raw = "Pub. L. 94-553, Oct. 19, 1976, 90 Stat. 2541."
        result = self._make_notes(raw)
        assert result.raw_notes == raw

    def test_empty_raw_notes(self) -> None:
        result = self._make_notes("")
        assert result.raw_notes == ""

    def test_combined_markers(self) -> None:
        raw = (
            "[NH]References In Text[/NH] "
            "The term means: [QC:1]as defined by section 101.[/QC] "
            "[H2]Definition[/H2] Further clarification."
        )
        result = self._make_notes(raw)
        assert "[NH]" not in result.raw_notes
        assert "[QC:" not in result.raw_notes
        assert "[H2]" not in result.raw_notes
        assert "as defined by section 101." in result.raw_notes
        assert "Definition" in result.raw_notes
        assert "Further clarification." in result.raw_notes
