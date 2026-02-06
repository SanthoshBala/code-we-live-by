"""widen us_code_section heading to text

Revision ID: a1b2c3d4e5f6
Revises: cfeb4ccf0b6c
Create Date: 2026-02-06 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "cfeb4ccf0b6c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "us_code_section",
        "heading",
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "us_code_section",
        "heading",
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=False,
    )
