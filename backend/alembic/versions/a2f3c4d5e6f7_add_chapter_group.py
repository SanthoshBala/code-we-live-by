"""Add us_code_chapter_group table and group_id to us_code_chapter

Revision ID: a2f3c4d5e6f7
Revises: b151e1b05c53
Create Date: 2026-02-08 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2f3c4d5e6f7"
down_revision: str = "b151e1b05c53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create us_code_chapter_group table and add group_id FK to us_code_chapter."""
    op.create_table(
        "us_code_chapter_group",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("title_id", sa.Integer(), nullable=False),
        sa.Column("parent_group_id", sa.Integer(), nullable=True),
        sa.Column("group_type", sa.String(length=50), nullable=False),
        sa.Column("group_number", sa.String(length=50), nullable=False),
        sa.Column("group_name", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["title_id"],
            ["us_code_title.title_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_group_id"],
            ["us_code_chapter_group.group_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("group_id"),
        sa.UniqueConstraint(
            "title_id",
            "group_type",
            "group_number",
            "parent_group_id",
            name="uq_chapter_group_identity",
        ),
    )
    op.create_index("idx_chapter_group_title", "us_code_chapter_group", ["title_id"])
    op.create_index(
        "idx_chapter_group_parent", "us_code_chapter_group", ["parent_group_id"]
    )

    op.add_column(
        "us_code_chapter",
        sa.Column("group_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_chapter_group_id",
        "us_code_chapter",
        "us_code_chapter_group",
        ["group_id"],
        ["group_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Drop group_id FK from us_code_chapter and drop us_code_chapter_group table."""
    op.drop_constraint("fk_chapter_group_id", "us_code_chapter", type_="foreignkey")
    op.drop_column("us_code_chapter", "group_id")
    op.drop_index("idx_chapter_group_parent", table_name="us_code_chapter_group")
    op.drop_index("idx_chapter_group_title", table_name="us_code_chapter_group")
    op.drop_table("us_code_chapter_group")
