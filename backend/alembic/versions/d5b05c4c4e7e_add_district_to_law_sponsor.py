"""add_district_to_law_sponsor

Revision ID: d5b05c4c4e7e
Revises: ce275a30c5ec
Create Date: 2026-05-21 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5b05c4c4e7e"
down_revision: str | None = "ce275a30c5ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add district column to law_sponsor table."""
    op.add_column(
        "law_sponsor",
        sa.Column("district", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Remove district column from law_sponsor table."""
    op.drop_column("law_sponsor", "district")
