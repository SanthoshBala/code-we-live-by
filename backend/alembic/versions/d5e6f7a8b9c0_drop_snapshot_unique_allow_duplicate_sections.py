"""Drop section_snapshot unique constraint to allow duplicate sections.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-02-18

The US Code contains legitimate duplicate section numbers — Congress
occasionally enacts two different provisions with the same section number
(e.g. two § 4781 in Title 10). The OLRC preserves both in the XML with
a footnote: "So in original. Two sections 4781 have been enacted."

These duplicates are eventually cleaned up by a technical corrections law
(e.g. PL 115-91 repealed the duplicate § 4781). Until that happens, our
snapshot table needs to store both versions at the same revision.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_section_snapshot_revision_section",
        "section_snapshot",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_section_snapshot_revision_section",
        "section_snapshot",
        ["revision_id", "title_number", "section_number"],
    )
