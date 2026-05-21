"""backfill_t17_ch10_section_group

Backfill the missing SectionGroup for Title 17, Chapter 10
("Digital Audio Recording Devices and Media", §§1001–1010).

Chapter 10 was absent from the structure endpoint (issue #215) because
it was ingested before the SectionGroup model existed.  The group row
was never created and sections 1001–1010 carry group_id = NULL.

This migration:
  1. Inserts the SectionGroup for chapter:10 under title:17.
  2. Updates section_snapshot.group_id for §§1001–1010 of title 17.
  3. Updates us_code_section.group_id for §§1001–1010 of title 17.

Group UUIDs are the deterministic UUID5 values produced by
pipeline.olrc.group_service.group_id_from_key:
  title:17            → aae4c5a6-db32-5662-91ae-e53b1f162ee5
  title:17/chapter:10 → dabd190c-3193-5cae-acdf-338267a2d869

Revision ID: 883637321672
Revises: ce275a30c5ec
Create Date: 2026-05-20 19:27:33.563904
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "883637321672"
down_revision: str | None = "ce275a30c5ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TITLE17_GROUP_ID = "aae4c5a6-db32-5662-91ae-e53b1f162ee5"
_CH10_GROUP_ID = "dabd190c-3193-5cae-acdf-338267a2d869"
_CH10_SECTIONS = [str(n) for n in range(1001, 1011)]


def upgrade() -> None:
    """Insert the missing Chapter 10 SectionGroup and wire §§1001–1010."""
    conn = op.get_bind()

    # 1. Insert Chapter 10 group (idempotent — skip if already present).
    conn.execute(
        sa.text("""
            INSERT INTO section_group
                (group_id, parent_id, group_type, number, name, sort_order,
                 is_positive_law, positive_law_date, positive_law_citation,
                 created_at, updated_at)
            SELECT
                :ch10_id::uuid,
                :title17_id::uuid,
                'chapter',
                '10',
                'Digital Audio Recording Devices and Media',
                999,
                TRUE,
                (SELECT positive_law_date FROM section_group
                 WHERE group_id = :title17_id::uuid),
                (SELECT positive_law_citation FROM section_group
                 WHERE group_id = :title17_id::uuid),
                now(),
                now()
            WHERE EXISTS (
                SELECT 1 FROM section_group WHERE group_id = :title17_id::uuid
            )
            ON CONFLICT (group_id) DO NOTHING
        """),
        {"ch10_id": _CH10_GROUP_ID, "title17_id": _TITLE17_GROUP_ID},
    )

    # 2. Assign group_id in section_snapshot for §§1001–1010 of title 17.
    conn.execute(
        sa.text("""
            UPDATE section_snapshot
            SET group_id = :ch10_id::uuid
            WHERE title_number = 17
              AND section_number = ANY(:sections)
              AND group_id IS NULL
        """),
        {"ch10_id": _CH10_GROUP_ID, "sections": _CH10_SECTIONS},
    )

    # 3. Assign group_id in us_code_section for §§1001–1010 of title 17.
    conn.execute(
        sa.text("""
            UPDATE us_code_section
            SET group_id = :ch10_id::uuid
            WHERE title_number = 17
              AND section_number = ANY(:sections)
              AND group_id IS NULL
        """),
        {"ch10_id": _CH10_GROUP_ID, "sections": _CH10_SECTIONS},
    )


def downgrade() -> None:
    """Remove the Chapter 10 group and clear its group_id references."""
    conn = op.get_bind()

    conn.execute(
        sa.text("""
            UPDATE section_snapshot
            SET group_id = NULL
            WHERE group_id = :ch10_id::uuid
        """),
        {"ch10_id": _CH10_GROUP_ID},
    )

    conn.execute(
        sa.text("""
            UPDATE us_code_section
            SET group_id = NULL
            WHERE group_id = :ch10_id::uuid
        """),
        {"ch10_id": _CH10_GROUP_ID},
    )

    conn.execute(
        sa.text("DELETE FROM section_group WHERE group_id = :ch10_id::uuid"),
        {"ch10_id": _CH10_GROUP_ID},
    )
