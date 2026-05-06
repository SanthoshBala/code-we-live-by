"""section_group: replace integer PK/FK with deterministic UUID

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-05-06

Converts section_group.group_id (and all FK columns that reference it) from
a DB-generated integer serial to an application-assigned UUID5.  The UUID is
derived from the group's full hierarchy key (e.g. "title:17/chapter:1") using
the fixed project namespace _GROUP_NS defined in group_service.py.

For each existing row the key path is reconstructed via a recursive CTE, the
UUID is computed in Python, and the new value is written back before the old
integer columns are dropped.

Column changes
--------------
section_group     : group_id  INTEGER PK → UUID PK
                    parent_id INTEGER FK → UUID FK
us_code_section   : group_id  INTEGER FK → UUID FK (nullable)
section_snapshot  : group_id  INTEGER FK → UUID FK (nullable)
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers
revision: str = "a8b9c0d1e2f3"
down_revision: str = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must match pipeline/olrc/group_service.py _GROUP_NS — never change.
_GROUP_NS = uuid.UUID("6f3a4b5c-2d1e-4f0a-9c8d-7e6f5d4c3b2a")


def _build_id_map(conn: sa.engine.Connection) -> dict[int, uuid.UUID]:
    """Reconstruct the hierarchy key for every section_group row and compute
    its deterministic UUID.  Returns {old_integer_id: new_uuid}.
    """
    rows = conn.execute(
        text("""
            WITH RECURSIVE group_path AS (
                SELECT group_id,
                       group_type || ':' || number AS key_path
                FROM   section_group
                WHERE  parent_id IS NULL
                UNION ALL
                SELECT sg.group_id,
                       gp.key_path || '/' || sg.group_type || ':' || sg.number
                FROM   section_group sg
                JOIN   group_path   gp ON sg.parent_id = gp.group_id
            )
            SELECT group_id, key_path FROM group_path
        """)
    ).fetchall()
    return {row.group_id: uuid.uuid5(_GROUP_NS, row.key_path) for row in rows}


def upgrade() -> None:
    conn = op.get_bind()
    id_map = _build_id_map(conn)

    # ------------------------------------------------------------------ #
    # 1. Add temporary UUID shadow columns (nullable for now)              #
    # ------------------------------------------------------------------ #
    op.add_column(
        "section_group", sa.Column("_new_gid", UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        "section_group", sa.Column("_new_pid", UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        "us_code_section", sa.Column("_new_gid", UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        "section_snapshot", sa.Column("_new_gid", UUID(as_uuid=True), nullable=True)
    )

    # ------------------------------------------------------------------ #
    # 2. Backfill shadow columns using the computed UUID mapping           #
    # ------------------------------------------------------------------ #
    if id_map:
        # Use a temporary table for the bulk update — avoids giant IN() lists.
        conn.execute(
            text(
                "CREATE TEMPORARY TABLE _gid_map (old_id integer PRIMARY KEY, new_id uuid NOT NULL)"
            )
        )
        conn.execute(
            text("INSERT INTO _gid_map VALUES (:old_id, :new_id)"),
            [{"old_id": k, "new_id": str(v)} for k, v in id_map.items()],
        )

        conn.execute(
            text("""
            UPDATE section_group sg
            SET    _new_gid = m.new_id
            FROM   _gid_map m
            WHERE  sg.group_id = m.old_id
        """)
        )
        conn.execute(
            text("""
            UPDATE section_group sg
            SET    _new_pid = m.new_id
            FROM   _gid_map m
            WHERE  sg.parent_id = m.old_id
        """)
        )
        conn.execute(
            text("""
            UPDATE us_code_section ucs
            SET    _new_gid = m.new_id
            FROM   _gid_map m
            WHERE  ucs.group_id = m.old_id
        """)
        )
        conn.execute(
            text("""
            UPDATE section_snapshot ss
            SET    _new_gid = m.new_id
            FROM   _gid_map m
            WHERE  ss.group_id = m.old_id
        """)
        )

        conn.execute(text("DROP TABLE _gid_map"))

    # ------------------------------------------------------------------ #
    # 3. Drop FK constraints and indexes that reference the old columns    #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_section_group_parent_id_section_group", "section_group", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_us_code_section_group_id_section_group",
        "us_code_section",
        type_="foreignkey",
    )
    # section_snapshot FK was added via add_column with inline ForeignKey,
    # so PostgreSQL named it with the standard convention.
    op.drop_constraint(
        "section_snapshot_group_id_fkey", "section_snapshot", type_="foreignkey"
    )

    op.drop_constraint("uq_section_group_child", "section_group", type_="unique")
    op.drop_index("idx_section_group_parent", "section_group")
    op.drop_index("idx_section_group_sort", "section_group")
    op.drop_index("idx_section_group", "us_code_section")
    op.drop_index("idx_section_sort", "us_code_section")
    op.drop_index("idx_section_snapshot_group", "section_snapshot")

    # ------------------------------------------------------------------ #
    # 4. Drop PK constraint so we can drop the old integer column          #
    # ------------------------------------------------------------------ #
    op.drop_constraint("pk_section_group", "section_group", type_="primary")

    # ------------------------------------------------------------------ #
    # 5. Drop old integer columns                                          #
    # ------------------------------------------------------------------ #
    op.drop_column("section_group", "group_id")
    op.drop_column("section_group", "parent_id")
    op.drop_column("us_code_section", "group_id")
    op.drop_column("section_snapshot", "group_id")

    # ------------------------------------------------------------------ #
    # 6. Rename shadow columns to final names                              #
    # ------------------------------------------------------------------ #
    op.alter_column("section_group", "_new_gid", new_column_name="group_id")
    op.alter_column("section_group", "_new_pid", new_column_name="parent_id")
    op.alter_column("us_code_section", "_new_gid", new_column_name="group_id")
    op.alter_column("section_snapshot", "_new_gid", new_column_name="group_id")

    # ------------------------------------------------------------------ #
    # 7. Add NOT NULL + PK on section_group.group_id                       #
    # ------------------------------------------------------------------ #
    op.alter_column("section_group", "group_id", nullable=False)
    op.create_primary_key("pk_section_group", "section_group", ["group_id"])

    # ------------------------------------------------------------------ #
    # 8. Recreate FK constraints                                           #
    # ------------------------------------------------------------------ #
    op.create_foreign_key(
        "fk_section_group_parent_id_section_group",
        "section_group",
        "section_group",
        ["parent_id"],
        ["group_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_us_code_section_group_id_section_group",
        "us_code_section",
        "section_group",
        ["group_id"],
        ["group_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_section_snapshot_group_id_section_group",
        "section_snapshot",
        "section_group",
        ["group_id"],
        ["group_id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------------ #
    # 9. Recreate unique constraint and indexes                            #
    # ------------------------------------------------------------------ #
    op.create_unique_constraint(
        "uq_section_group_child",
        "section_group",
        ["parent_id", "group_type", "number"],
    )
    op.create_index("idx_section_group_parent", "section_group", ["parent_id"])
    op.create_index(
        "idx_section_group_sort", "section_group", ["parent_id", "sort_order"]
    )
    op.create_index("idx_section_group", "us_code_section", ["group_id"])
    op.create_index("idx_section_sort", "us_code_section", ["group_id", "sort_order"])
    op.create_index("idx_section_snapshot_group", "section_snapshot", ["group_id"])


def downgrade() -> None:
    # Downgrade is intentionally not implemented: reverting a UUID→integer PK
    # migration would require re-assigning sequential IDs and is not safe to
    # do automatically.  Restore from a pre-migration backup instead.
    raise NotImplementedError(
        "Downgrade from UUID group_id is not supported. "
        "Restore from a pre-migration backup."
    )
