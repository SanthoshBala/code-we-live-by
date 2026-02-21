"""Add Add_Note to changetype enum.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-02-21

Freestanding law sections (study mandates, findings, short titles) that
don't amend existing US Code text are captured by the OLRC as <note>
elements. This migration adds the Add_Note change type to support them.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE changetype ADD VALUE IF NOT EXISTS 'Add_Note'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    pass
