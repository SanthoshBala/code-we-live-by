"""add_signing_statement_to_public_law

Revision ID: ce275a30c5ec
Revises: 08cdb229431e
Create Date: 2026-05-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "ce275a30c5ec"
down_revision: str | None = "08cdb229431e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add signing_statement and signing_statement_url columns to public_law."""
    op.add_column(
        "public_law", sa.Column("signing_statement", sa.Text(), nullable=True)
    )
    op.add_column(
        "public_law",
        sa.Column("signing_statement_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Remove signing statement columns from public_law."""
    op.drop_column("public_law", "signing_statement_url")
    op.drop_column("public_law", "signing_statement")
