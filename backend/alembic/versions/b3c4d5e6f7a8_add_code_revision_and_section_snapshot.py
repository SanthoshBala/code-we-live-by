"""Add code_revision and section_snapshot tables.

Revision ID: b3c4d5e6f7a8
Revises: a2f3b8c1d4e5
Create Date: 2026-02-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a2f3b8c1d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum types via raw DDL so we can use IF NOT EXISTS,
    # which asyncpg handles reliably (sa.Enum checkfirst has issues
    # with asyncpg, and create_table re-creates enums implicitly).
    op.execute("CREATE TYPE revision_type_enum AS ENUM ('Release_Point', 'Public_Law')")
    op.execute(
        "CREATE TYPE revision_status_enum AS ENUM "
        "('Pending', 'Ingesting', 'Ingested', 'Failed')"
    )

    # Reference the already-created types via postgresql.ENUM with
    # create_type=False so create_table doesn't issue a second CREATE TYPE.
    revision_type_enum = postgresql.ENUM(
        "Release_Point", "Public_Law", name="revision_type_enum", create_type=False
    )
    revision_status_enum = postgresql.ENUM(
        "Pending",
        "Ingesting",
        "Ingested",
        "Failed",
        name="revision_status_enum",
        create_type=False,
    )

    # code_revision table
    op.create_table(
        "code_revision",
        sa.Column("revision_id", sa.Integer(), nullable=False),
        sa.Column("revision_type", revision_type_enum, nullable=False),
        sa.Column(
            "release_point_id",
            sa.Integer(),
            sa.ForeignKey("olrc_release_point.release_point_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "law_id",
            sa.Integer(),
            sa.ForeignKey("public_law.law_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "parent_revision_id",
            sa.Integer(),
            sa.ForeignKey("code_revision.revision_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "is_ground_truth", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "status",
            revision_status_enum,
            nullable=False,
            server_default="Pending",
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("revision_id", name="pk_code_revision"),
        sa.UniqueConstraint("release_point_id", name="uq_code_revision_release_point"),
        sa.UniqueConstraint("law_id", name="uq_code_revision_law"),
        sa.UniqueConstraint("sequence_number", name="uq_code_revision_sequence"),
    )
    op.create_index(
        "idx_code_revision_parent",
        "code_revision",
        ["parent_revision_id"],
    )
    op.create_index(
        "idx_code_revision_effective_date",
        "code_revision",
        ["effective_date"],
    )
    op.create_index(
        "idx_code_revision_status",
        "code_revision",
        ["status"],
    )

    # section_snapshot table
    op.create_table(
        "section_snapshot",
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("code_revision.revision_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title_number", sa.Integer(), nullable=False),
        sa.Column("section_number", sa.String(100), nullable=False),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("normalized_provisions", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("normalized_notes", postgresql.JSONB(), nullable=True),
        sa.Column("text_hash", sa.String(64), nullable=True),
        sa.Column("notes_hash", sa.String(64), nullable=True),
        sa.Column("full_citation", sa.String(200), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("snapshot_id", name="pk_section_snapshot"),
        sa.UniqueConstraint(
            "revision_id",
            "title_number",
            "section_number",
            name="uq_section_snapshot_revision_section",
        ),
    )
    op.create_index(
        "idx_section_snapshot_title_section",
        "section_snapshot",
        ["title_number", "section_number"],
    )
    op.create_index(
        "idx_section_snapshot_text_hash",
        "section_snapshot",
        ["text_hash"],
    )


def downgrade() -> None:
    op.drop_index("idx_section_snapshot_text_hash", table_name="section_snapshot")
    op.drop_index("idx_section_snapshot_title_section", table_name="section_snapshot")
    op.drop_table("section_snapshot")

    op.drop_index("idx_code_revision_status", table_name="code_revision")
    op.drop_index("idx_code_revision_effective_date", table_name="code_revision")
    op.drop_index("idx_code_revision_parent", table_name="code_revision")
    op.drop_table("code_revision")

    # Drop enum types
    sa.Enum(name="revision_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="revision_type_enum").drop(op.get_bind(), checkfirst=True)
