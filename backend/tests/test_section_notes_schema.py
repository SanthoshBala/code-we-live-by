"""Tests for SectionNotesSchema — specifically the raw_notes markup-stripping validator."""

from app.models.enums import SourceRelationship
from app.schemas.public_law import SourceLawSchema
from app.schemas.us_code import NoteCategoryEnum, SectionNoteSchema, SectionNotesSchema


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


class TestSourceLawSchemaRawTextStripping:
    """SourceLawSchema.raw_text must have [NH]..[/NH] tags stripped (Issue #458).

    When a note topic attribute is synthesised into an [NH]...[/NH] marker and
    that marker ends up prepended to the citation text (because the note block
    has no other separator), the raw_text field previously leaked the tag into
    the API response.  Example from 37 U.S.C. § 426:

        raw_text was: "[NH]Removaldescription[/NH]\\n\\nSection, Pub. L. 87-649..."
        raw_text should be: "Section, Pub. L. 87-649..."
    """

    def _make_citation(self, raw_text: str) -> SourceLawSchema:
        return SourceLawSchema.model_validate(
            {
                "law": {
                    "congress": 87,
                    "law_number": 649,
                },
                "relationship": SourceRelationship.ENACTMENT,
                "raw_text": raw_text,
            }
        )

    def test_nh_tag_stripped_from_raw_text(self) -> None:
        """[NH]...[/NH] tag is removed and the citation text is preserved."""
        raw = "[NH]Removaldescription[/NH]\n\nSection, Pub. L. 87-649, Sept. 7, 1962, 76 Stat. 451."
        result = self._make_citation(raw)
        assert "[NH]" not in result.raw_text
        assert "[/NH]" not in result.raw_text
        assert "Pub. L. 87-649" in result.raw_text

    def test_nh_tag_with_multiword_topic_stripped(self) -> None:
        """[NH] tag with multi-word note topic is fully removed."""
        raw = "[NH]Effective Date Of 2013 Amendment[/NH] Pub. L. 113-66, § 631, Dec. 26, 2013."
        result = self._make_citation(raw)
        assert "[NH]" not in result.raw_text
        assert "[/NH]" not in result.raw_text
        assert "Pub. L. 113-66" in result.raw_text

    def test_plain_citation_unchanged(self) -> None:
        """Citations without any [NH] markup are returned as-is."""
        raw = "Pub. L. 87-649, Sept. 7, 1962, 76 Stat. 451."
        result = self._make_citation(raw)
        assert result.raw_text == raw

    def test_orphaned_closing_tag_stripped(self) -> None:
        """A stray [/NH] closing tag without an opening tag is also removed."""
        raw = "[/NH] Pub. L. 87-649, Sept. 7, 1962, 76 Stat. 451."
        result = self._make_citation(raw)
        assert "[/NH]" not in result.raw_text
        assert "Pub. L. 87-649" in result.raw_text


class TestHasAmendments:
    """Tests for SectionNotesSchema.has_amendments (issue #571).

    9 U.S.C. § 4 was amended in 1954 by a pre-Public-Law chapter act.
    The section was ingested before chapter-act support was added, so
    ``notes.amendments`` is empty in the DB.  Despite this, the section
    has an ``"Amendments"`` editorial note and a non-original citation.
    ``has_amendments`` must return True in all such cases.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _amendments_note() -> SectionNoteSchema:
        """Return a minimal Amendments editorial note (mirrors 9 U.S.C. § 4)."""
        return SectionNoteSchema(
            header="Amendments",
            category=NoteCategoryEnum.EDITORIAL,
            lines=[],
        )

    @staticmethod
    def _act_citation(order: int) -> dict:
        """Return a dict suitable for SourceLawSchema.model_validate with a pre-1957 Act."""
        dates = {0: "1947-07-30", 1: "1954-09-03"}
        chapters = {0: "392", 1: "1263"}
        raws = {
            0: "July 30, 1947, ch. 392, 61 Stat. 671",
            1: "Sept. 3, 1954, ch. 1263, § 19, 68 Stat. 1233",
        }
        return {
            "act": {"date": dates[order], "chapter": chapters[order]},
            "relationship": "Framework",
            "raw_text": raws[order],
            "order": order,
        }

    # ------------------------------------------------------------------
    # Baseline: all sources empty
    # ------------------------------------------------------------------

    def test_false_when_no_amendments_at_all(self) -> None:
        """has_amendments is False when amendments list, notes, and citations are empty."""
        notes = SectionNotesSchema()
        assert notes.has_amendments is False

    def test_false_when_only_original_citation(self) -> None:
        """has_amendments is False when there is only a single (original) citation."""
        citation = SourceLawSchema.model_validate(self._act_citation(0))
        notes = SectionNotesSchema(citations=[citation])
        assert notes.has_amendments is False

    # ------------------------------------------------------------------
    # Source 1: structured amendments list
    # ------------------------------------------------------------------

    def test_true_from_structured_amendments_list(self) -> None:
        """has_amendments is True when the structured amendments list is non-empty."""
        from app.schemas.us_code import AmendmentSchema

        notes = SectionNotesSchema(
            amendments=[AmendmentSchema(year=1954, description="Amended by Act.")]
        )
        assert notes.has_amendments is True

    # ------------------------------------------------------------------
    # Source 2: "Amendments" header in notes.notes
    # ------------------------------------------------------------------

    def test_true_from_amendments_note_header(self) -> None:
        """has_amendments is True when notes.notes contains an Amendments header."""
        notes = SectionNotesSchema(
            amendments=[],
            notes=[self._amendments_note()],
        )
        assert notes.has_amendments is True

    def test_false_when_only_non_amendments_note_header(self) -> None:
        """has_amendments is False when the only note header is not 'Amendments'."""
        notes = SectionNotesSchema(
            amendments=[],
            notes=[
                SectionNoteSchema(
                    header="References In Text",
                    category=NoteCategoryEnum.EDITORIAL,
                )
            ],
        )
        assert notes.has_amendments is False

    # ------------------------------------------------------------------
    # Source 3: non-original citation
    # ------------------------------------------------------------------

    def test_true_from_non_original_citation(self) -> None:
        """has_amendments is True when any citation has is_original False (order > 0)."""
        citations = [
            SourceLawSchema.model_validate(self._act_citation(0)),
            SourceLawSchema.model_validate(self._act_citation(1)),
        ]
        notes = SectionNotesSchema(amendments=[], citations=citations)
        assert notes.has_amendments is True

    # ------------------------------------------------------------------
    # 9 U.S.C. § 4 regression (issue #571)
    # ------------------------------------------------------------------

    def test_9usc4_scenario_has_amendments_true(self) -> None:
        """9 U.S.C. § 4: has_amendments is True even when amendments list is empty.

        The section was amended in 1954 by Act ch. 1263, § 19, but was ingested
        before pre-PL chapter-act support was added so notes.amendments is [].
        Both the Amendments editorial note (source 2) and the non-original
        citation (source 3) must independently produce has_amendments=True.
        """
        citations = [
            SourceLawSchema.model_validate(self._act_citation(0)),
            SourceLawSchema.model_validate(self._act_citation(1)),
        ]
        notes = SectionNotesSchema(
            amendments=[],
            notes=[self._amendments_note()],
            citations=citations,
        )
        # Both source-2 and source-3 fire; overall result must be True.
        assert notes.has_amendments is True

    def test_9usc4_scenario_source2_alone_suffices(self) -> None:
        """Amendments note alone (no citation) is sufficient for has_amendments=True."""
        notes = SectionNotesSchema(
            amendments=[],
            notes=[self._amendments_note()],
            citations=[SourceLawSchema.model_validate(self._act_citation(0))],
        )
        # Only one citation, is_original=True → source 3 does NOT fire.
        # Source 2 (Amendments note) must still produce True.
        assert notes.has_amendments is True

    def test_9usc4_scenario_source3_alone_suffices(self) -> None:
        """Non-original citation alone (no Amendments note) gives has_amendments=True."""
        citations = [
            SourceLawSchema.model_validate(self._act_citation(0)),
            SourceLawSchema.model_validate(self._act_citation(1)),
        ]
        notes = SectionNotesSchema(amendments=[], notes=[], citations=citations)
        # Source 3 fires (citation at order=1 → is_original=False).
        assert notes.has_amendments is True
