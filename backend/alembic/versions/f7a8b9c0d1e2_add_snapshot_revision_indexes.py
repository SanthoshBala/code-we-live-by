"""Add revision_id indexes to section_snapshot for query performance.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-03-24

Adds two indexes to section_snapshot:
  - idx_section_snapshot_revision: covers WHERE revision_id = ANY(:chain)
  - idx_section_snapshot_rev_title_section: composite for per-title lookups
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_section_snapshot_revision",
        "section_snapshot",
        ["revision_id"],
    )
    op.create_index(
        "idx_section_snapshot_rev_title_section",
        "section_snapshot",
        ["revision_id", "title_number", "section_number"],
    )


def downgrade() -> None:
    op.drop_index("idx_section_snapshot_rev_title_section", "section_snapshot")
    op.drop_index("idx_section_snapshot_revision", "section_snapshot")
