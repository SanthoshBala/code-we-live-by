"""add_codeowners_tables

Revision ID: 19521111cd88
Revises: ce275a30c5ec
Create Date: 2026-05-19 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "19521111cd88"
down_revision: str | None = "ce275a30c5ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add CODEOWNERS tables and widen committee_code to support readable slugs."""
    # Widen committee.committee_code from VARCHAR(20) to VARCHAR(100).
    # The Committee table is currently empty (no pipeline populates it yet),
    # so this is safe. Required for slugs like "house-education-and-workforce".
    op.alter_column(
        "committee",
        "committee_code",
        type_=sa.String(length=100),
        existing_nullable=False,
    )

    op.create_table(
        "committee_congress_instance",
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("committee_id", sa.Integer(), nullable=False),
        sa.Column("congress", sa.Integer(), nullable=False),
        sa.Column("official_name", sa.String(length=300), nullable=False),
        sa.Column("rule_citation", sa.String(length=100), nullable=True),
        sa.Column("jurisdiction_text", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["committee_id"],
            ["committee.committee_id"],
            name=op.f("fk_committee_congress_instance_committee_id_committee"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "instance_id", name=op.f("pk_committee_congress_instance")
        ),
        sa.UniqueConstraint(
            "committee_id",
            "congress",
            name="uq_cci_committee_congress",
        ),
    )
    op.create_index("idx_cci_congress", "committee_congress_instance", ["congress"])
    op.create_index(
        "idx_cci_committee_id", "committee_congress_instance", ["committee_id"]
    )

    op.create_table(
        "committee_usc_mapping",
        sa.Column("mapping_id", sa.Integer(), nullable=False),
        sa.Column("committee_id", sa.Integer(), nullable=False),
        sa.Column("congress_start", sa.Integer(), nullable=False),
        sa.Column("congress_end", sa.Integer(), nullable=True),
        sa.Column("title_number", sa.Integer(), nullable=False),
        sa.Column("chapter_number", sa.String(length=20), nullable=True),
        sa.Column("jurisdiction_type", sa.String(length=20), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "jurisdiction_type IN ('primary', 'secondary', 'oversight')",
            name=op.f("ck_committee_usc_mapping_cum_jurisdiction_type"),
        ),
        sa.CheckConstraint(
            "congress_end IS NULL OR congress_end >= congress_start",
            name=op.f("ck_committee_usc_mapping_cum_congress_range"),
        ),
        sa.ForeignKeyConstraint(
            ["committee_id"],
            ["committee.committee_id"],
            name=op.f("fk_committee_usc_mapping_committee_id_committee"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("mapping_id", name=op.f("pk_committee_usc_mapping")),
        sa.UniqueConstraint(
            "committee_id",
            "congress_start",
            "title_number",
            "chapter_number",
            "jurisdiction_type",
            name="uq_cum_committee_congress_path_type",
        ),
    )
    op.create_index("idx_cum_title", "committee_usc_mapping", ["title_number"])
    op.create_index(
        "idx_cum_title_chapter",
        "committee_usc_mapping",
        ["title_number", "chapter_number"],
    )
    op.create_index("idx_cum_committee_id", "committee_usc_mapping", ["committee_id"])
    op.create_index(
        "idx_cum_congress_range",
        "committee_usc_mapping",
        ["congress_start", "congress_end"],
    )


def downgrade() -> None:
    """Remove CODEOWNERS tables and restore committee_code width."""
    op.drop_index("idx_cum_congress_range", table_name="committee_usc_mapping")
    op.drop_index("idx_cum_committee_id", table_name="committee_usc_mapping")
    op.drop_index("idx_cum_title_chapter", table_name="committee_usc_mapping")
    op.drop_index("idx_cum_title", table_name="committee_usc_mapping")
    op.drop_table("committee_usc_mapping")

    op.drop_index("idx_cci_committee_id", table_name="committee_congress_instance")
    op.drop_index("idx_cci_congress", table_name="committee_congress_instance")
    op.drop_table("committee_congress_instance")

    op.alter_column(
        "committee",
        "committee_code",
        type_=sa.String(length=20),
        existing_nullable=False,
    )
