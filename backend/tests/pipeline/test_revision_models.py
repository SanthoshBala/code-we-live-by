"""Tests for CodeRevision and SectionSnapshot models."""

from app.models.enums import RevisionStatus, RevisionType


class TestRevisionType:
    """Tests for RevisionType enum."""

    def test_values(self) -> None:
        assert RevisionType.RELEASE_POINT == "Release_Point"
        assert RevisionType.PUBLIC_LAW == "Public_Law"

    def test_str_enum(self) -> None:
        assert isinstance(RevisionType.RELEASE_POINT, str)
        assert RevisionType.RELEASE_POINT.value == "Release_Point"


class TestRevisionStatus:
    """Tests for RevisionStatus enum."""

    def test_values(self) -> None:
        assert RevisionStatus.PENDING == "Pending"
        assert RevisionStatus.INGESTING == "Ingesting"
        assert RevisionStatus.INGESTED == "Ingested"
        assert RevisionStatus.FAILED == "Failed"

    def test_all_statuses(self) -> None:
        statuses = list(RevisionStatus)
        assert len(statuses) == 4


class TestCodeRevisionModel:
    """Tests for CodeRevision model structure."""

    def test_import(self) -> None:
        from app.models.revision import CodeRevision

        assert CodeRevision.__tablename__ == "code_revision"

    def test_table_args(self) -> None:
        from app.models.revision import CodeRevision

        # Verify unique constraints and indexes exist
        table_args = CodeRevision.__table_args__
        constraint_names = {arg.name for arg in table_args if hasattr(arg, "name")}
        assert "uq_code_revision_release_point" in constraint_names
        assert "uq_code_revision_law" in constraint_names
        assert "uq_code_revision_sequence" in constraint_names
        assert "idx_code_revision_parent" in constraint_names
        assert "idx_code_revision_effective_date" in constraint_names
        assert "idx_code_revision_status" in constraint_names


class TestSectionSnapshotModel:
    """Tests for SectionSnapshot model structure."""

    def test_import(self) -> None:
        from app.models.snapshot import SectionSnapshot

        assert SectionSnapshot.__tablename__ == "section_snapshot"

    def test_table_args(self) -> None:
        from app.models.snapshot import SectionSnapshot

        table_args = SectionSnapshot.__table_args__
        constraint_names = {arg.name for arg in table_args if hasattr(arg, "name")}
        # No unique constraint — duplicate section numbers are legitimate in the US Code
        assert "uq_section_snapshot_revision_section" not in constraint_names
        assert "idx_section_snapshot_title_section" in constraint_names
        assert "idx_section_snapshot_text_hash" in constraint_names
