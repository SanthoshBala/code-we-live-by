"""Add law_bill_action and law_sponsor tables for caching legislative history.

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-05-06

Adds two tables:
  - law_bill_action: cached bill actions (timeline events) per public law
  - law_sponsor: cached primary sponsor + cosponsors per public law

Both are populated by the seed-law-history pipeline command so the History
tab can serve responses from the DB instead of hitting Congress.gov on every
request.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "law_bill_action",
        sa.Column("action_id", sa.Integer(), nullable=False),
        sa.Column("law_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("action_date", sa.Date(), nullable=True),
        sa.Column("action_code", sa.String(length=50), nullable=True),
        sa.Column("action_type", sa.String(length=100), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("chamber", sa.String(length=50), nullable=True),
        sa.Column(
            "congressional_record_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("is_milestone", sa.Boolean(), nullable=False),
        sa.Column("vote_yeas", sa.Integer(), nullable=True),
        sa.Column("vote_nays", sa.Integer(), nullable=True),
        sa.Column("vote_not_voting", sa.Integer(), nullable=True),
        sa.Column("event_title", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["law_id"],
            ["public_law.law_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("action_id"),
    )
    op.create_index(
        "idx_law_bill_action_law_id", "law_bill_action", ["law_id"], unique=False
    )
    op.create_index(
        "idx_law_bill_action_sort",
        "law_bill_action",
        ["law_id", "sort_order"],
        unique=False,
    )

    op.create_table(
        "law_sponsor",
        sa.Column("sponsor_id", sa.Integer(), nullable=False),
        sa.Column("law_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("party", sa.String(length=20), nullable=True),
        sa.Column("state", sa.String(length=10), nullable=True),
        sa.Column("bioguide_id", sa.String(length=20), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["law_id"],
            ["public_law.law_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("sponsor_id"),
    )
    op.create_index("idx_law_sponsor_law_id", "law_sponsor", ["law_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_law_sponsor_law_id", table_name="law_sponsor")
    op.drop_table("law_sponsor")
    op.drop_index("idx_law_bill_action_sort", table_name="law_bill_action")
    op.drop_index("idx_law_bill_action_law_id", table_name="law_bill_action")
    op.drop_table("law_bill_action")
