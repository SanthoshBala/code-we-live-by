"""LawChange natural keys, SectionSnapshot group_id.

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-02-18

Migrates LawChange from section_id FK to natural keys (title_number,
section_number). Adds group_id and sort_order to SectionSnapshot for
navigation hierarchy.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- LawChange: add natural key columns (nullable first) --
    op.add_column(
        "law_change",
        sa.Column("title_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "law_change",
        sa.Column("section_number", sa.String(100), nullable=True),
    )

    # Data migration: populate from us_code_section via section_id
    op.execute(
        """
        UPDATE law_change
        SET title_number = s.title_number,
            section_number = s.section_number
        FROM us_code_section s
        WHERE law_change.section_id = s.section_id
        """
    )

    # Make columns NOT NULL
    op.alter_column("law_change", "title_number", nullable=False)
    op.alter_column("law_change", "section_number", nullable=False)

    # Drop old FK, index, and column
    op.drop_constraint(
        "fk_law_change_section_id_us_code_section", "law_change", type_="foreignkey"
    )
    op.drop_index("idx_change_section", table_name="law_change")
    op.drop_index("idx_change_law_section", table_name="law_change")
    op.drop_column("law_change", "section_id")

    # Add new indexes
    op.create_index(
        "idx_change_title_section",
        "law_change",
        ["title_number", "section_number"],
    )
    op.create_index(
        "idx_change_law_title_section",
        "law_change",
        ["law_id", "title_number", "section_number"],
    )

    # -- SectionSnapshot: add group_id and sort_order --
    op.add_column(
        "section_snapshot",
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("section_group.group_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "section_snapshot",
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index(
        "idx_section_snapshot_group",
        "section_snapshot",
        ["group_id"],
    )


def downgrade() -> None:
    # -- SectionSnapshot: remove group_id and sort_order --
    op.drop_index("idx_section_snapshot_group", table_name="section_snapshot")
    op.drop_column("section_snapshot", "sort_order")
    op.drop_column("section_snapshot", "group_id")

    # -- LawChange: restore section_id --
    op.add_column(
        "law_change",
        sa.Column("section_id", sa.Integer(), nullable=True),
    )

    # Reverse data migration
    op.execute(
        """
        UPDATE law_change
        SET section_id = s.section_id
        FROM us_code_section s
        WHERE law_change.title_number = s.title_number
          AND law_change.section_number = s.section_number
        """
    )

    op.alter_column("law_change", "section_id", nullable=False)
    op.create_foreign_key(
        "fk_law_change_section_id_us_code_section",
        "law_change",
        "us_code_section",
        ["section_id"],
        ["section_id"],
        ondelete="RESTRICT",
    )
    op.create_index("idx_change_section", "law_change", ["section_id"])
    op.create_index("idx_change_law_section", "law_change", ["law_id", "section_id"])

    # Drop new columns and indexes
    op.drop_index("idx_change_title_section", table_name="law_change")
    op.drop_index("idx_change_law_title_section", table_name="law_change")
    op.drop_column("law_change", "section_number")
    op.drop_column("law_change", "title_number")
