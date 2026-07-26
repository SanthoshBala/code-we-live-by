"""merge_codeowners_and_district_heads

Revision ID: 2249206d96b1
Revises: 19521111cd88, d5b05c4c4e7e
Create Date: 2026-07-25 19:47:28.805345
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "2249206d96b1"
down_revision: str | None = ("19521111cd88", "d5b05c4c4e7e")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade database schema."""
    pass


def downgrade() -> None:
    """Downgrade database schema."""
    pass
