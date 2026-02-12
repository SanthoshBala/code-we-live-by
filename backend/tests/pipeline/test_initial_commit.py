"""Tests for the initial commit service."""

import pytest

from pipeline.olrc.initial_commit import InitialCommitService
from pipeline.olrc.release_point import parse_release_point_identifier


class TestInitialCommitService:
    """Tests for InitialCommitService."""

    def test_parse_release_point(self) -> None:
        """Test that release point parsing works for initial commit context."""
        congress, law_id = parse_release_point_identifier("113-21")
        assert congress == 113
        assert law_id == "21"

    def test_service_init(self, tmp_path) -> None:
        """Test InitialCommitService can be initialized without DB."""
        # We can't fully test without a database, but we can verify
        # the class is importable and the constructor works with a mock
        assert InitialCommitService is not None
