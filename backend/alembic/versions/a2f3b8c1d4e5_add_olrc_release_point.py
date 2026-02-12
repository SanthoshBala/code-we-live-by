"""Add OLRC release point table.

Revision ID: a2f3b8c1d4e5
Revises: 31e77be6b0e1
Create Date: 2026-02-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2f3b8c1d4e5"
down_revision: Union[str, None] = "31e77be6b0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "olrc_release_point",
        sa.Column("release_point_id", sa.Integer(), nullable=False),
        sa.Column("full_identifier", sa.String(50), nullable=False),
        sa.Column("congress", sa.Integer(), nullable=False),
        sa.Column("law_identifier", sa.String(30), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("titles_updated", postgresql.JSONB(), nullable=True),
        sa.Column(
            "parent_release_point_id",
            sa.Integer(),
            sa.ForeignKey(
                "olrc_release_point.release_point_id", ondelete="SET NULL"
            ),
            nullable=True,
        ),
        sa.Column("is_initial", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ingested_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("release_point_id", name="pk_olrc_release_point"),
        sa.UniqueConstraint("full_identifier", name="uq_olrc_release_point_full_identifier"),
        sa.UniqueConstraint(
            "congress", "law_identifier", name="uq_release_point_congress_law"
        ),
    )
    op.create_index(
        "idx_release_point_congress",
        "olrc_release_point",
        ["congress"],
    )
    op.create_index(
        "idx_release_point_parent",
        "olrc_release_point",
        ["parent_release_point_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_release_point_parent", table_name="olrc_release_point")
    op.drop_index("idx_release_point_congress", table_name="olrc_release_point")
    op.drop_table("olrc_release_point")
