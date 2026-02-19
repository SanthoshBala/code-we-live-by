"""Checkpoint validation — compare derived state against RP ground truth.

Pure functions with no DB access. Takes two lists of SectionState and returns
a CheckpointResult describing matches and mismatches.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.olrc.snapshot_service import SectionState


@dataclass
class SectionMismatch:
    """A single section where derived state doesn't match RP ground truth."""

    title_number: int
    section_number: str
    mismatch_type: str  # "text", "notes", "both", "deleted_mismatch"
    derived_hash: str | None
    rp_hash: str | None


@dataclass
class CheckpointResult:
    """Result of comparing derived state against an RP checkpoint."""

    rp_identifier: str
    rp_revision_id: int
    derived_revision_id: int
    sections_match: int = 0
    sections_mismatch: int = 0
    sections_only_in_derived: int = 0
    sections_only_in_rp: int = 0
    mismatches: list[SectionMismatch] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """True if derived state perfectly matches RP ground truth."""
        return (
            self.sections_mismatch == 0
            and self.sections_only_in_derived == 0
            and self.sections_only_in_rp == 0
        )


def validate_checkpoint(
    derived_sections: list[SectionState],
    rp_sections: list[SectionState],
    rp_identifier: str,
    rp_revision_id: int,
    derived_revision_id: int,
) -> CheckpointResult:
    """Compare derived state against RP ground truth.

    Args:
        derived_sections: Sections from the last derived revision before the RP.
        rp_sections: Sections from the RP ground truth revision.
        rp_identifier: Release point identifier (e.g., "113-37").
        rp_revision_id: Revision ID of the RP.
        derived_revision_id: Revision ID of the last derived revision.

    Returns:
        CheckpointResult with match/mismatch counts and details.
    """
    result = CheckpointResult(
        rp_identifier=rp_identifier,
        rp_revision_id=rp_revision_id,
        derived_revision_id=derived_revision_id,
    )

    # Build lookup maps keyed by (title_number, section_number)
    derived_map: dict[tuple[int, str], SectionState] = {
        (s.title_number, s.section_number): s for s in derived_sections
    }
    rp_map: dict[tuple[int, str], SectionState] = {
        (s.title_number, s.section_number): s for s in rp_sections
    }

    all_keys = set(derived_map.keys()) | set(rp_map.keys())

    for key in sorted(all_keys):
        derived = derived_map.get(key)
        rp = rp_map.get(key)

        if derived is not None and rp is None:
            result.sections_only_in_derived += 1
            result.mismatches.append(
                SectionMismatch(
                    title_number=key[0],
                    section_number=key[1],
                    mismatch_type="only_in_derived",
                    derived_hash=derived.text_hash,
                    rp_hash=None,
                )
            )
            continue

        if derived is None and rp is not None:
            result.sections_only_in_rp += 1
            result.mismatches.append(
                SectionMismatch(
                    title_number=key[0],
                    section_number=key[1],
                    mismatch_type="only_in_rp",
                    derived_hash=None,
                    rp_hash=rp.text_hash,
                )
            )
            continue

        # Both exist — compare
        assert derived is not None and rp is not None

        # Check for deleted mismatch
        if derived.is_deleted != rp.is_deleted:
            result.sections_mismatch += 1
            result.mismatches.append(
                SectionMismatch(
                    title_number=key[0],
                    section_number=key[1],
                    mismatch_type="deleted_mismatch",
                    derived_hash=derived.text_hash,
                    rp_hash=rp.text_hash,
                )
            )
            continue

        # Both alive (or both deleted) — compare hashes
        text_match = derived.text_hash == rp.text_hash
        notes_match = derived.notes_hash == rp.notes_hash

        if text_match and notes_match:
            result.sections_match += 1
        else:
            result.sections_mismatch += 1
            if not text_match and not notes_match:
                mismatch_type = "both"
            elif not text_match:
                mismatch_type = "text"
            else:
                mismatch_type = "notes"
            result.mismatches.append(
                SectionMismatch(
                    title_number=key[0],
                    section_number=key[1],
                    mismatch_type=mismatch_type,
                    derived_hash=derived.text_hash,
                    rp_hash=rp.text_hash,
                )
            )

    return result
