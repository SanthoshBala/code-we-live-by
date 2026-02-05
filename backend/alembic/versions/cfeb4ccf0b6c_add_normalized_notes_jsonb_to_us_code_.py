"""add normalized_notes JSONB to us_code_section

Revision ID: cfeb4ccf0b6c
Revises: b151e1b05c53
Create Date: 2026-02-03 07:14:56.008845
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cfeb4ccf0b6c"
down_revision: str | None = "b151e1b05c53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add normalized_notes JSONB column to us_code_section."""
    op.add_column(
        "us_code_section",
        sa.Column(
            "normalized_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.create_index(
        "idx_section_normalized_notes_gin",
        "us_code_section",
        ["normalized_notes"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"normalized_notes": "jsonb_path_ops"},
    )


def downgrade() -> None:
    """Remove normalized_notes JSONB column from us_code_section."""
    op.drop_index("idx_section_normalized_notes_gin", table_name="us_code_section")
    op.drop_column("us_code_section", "normalized_notes")
