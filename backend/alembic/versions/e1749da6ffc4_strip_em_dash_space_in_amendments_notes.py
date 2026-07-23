"""strip_em_dash_space_in_amendments_notes

Strip the spurious space that older parser versions inserted between an
amendment-year em dash and the following "Pub. L." citation in the
normalized_notes JSONB cache.  For example, "2002— Pub. L. 107–273" should
be "2002—Pub. L. 107–273".

The parser bug was fixed in issue #600, but section_snapshot rows ingested
before that fix still store the artifact in their normalized_notes column.
This migration patches every affected row without requiring a full re-ingest.

See issue #626.

Revision ID: e1749da6ffc4
Revises: 19521111cd88
Create Date: 2026-07-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e1749da6ffc4"
down_revision: str | None = "19521111cd88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The em dash character (U+2014) followed by a space before "Pub." is the
# spurious artifact.  We replace every occurrence in the text representation
# of the JSONB and cast back to JSONB.  This safely fixes the pattern in
# notes[].lines[].content and in the raw_notes field without touching any
# field where a space after "—" would be intentional (no such field exists
# in SectionNotesSchema).
_FIX_SQL = """\
UPDATE {table}
SET normalized_notes = regexp_replace(
    normalized_notes::text,
    E'\\u2014 (?=Pub\\\\.)',
    E'\\u2014',
    'g'
)::jsonb
WHERE normalized_notes IS NOT NULL
  AND normalized_notes::text LIKE E'%— Pub.%'
"""


def upgrade() -> None:
    """Remove spurious spaces after em dashes in Amendments note lines."""
    for table in ("section_snapshot", "us_code_section"):
        op.execute(sa.text(_FIX_SQL.format(table=table)))


def downgrade() -> None:
    """No-op: restoring the spurious spaces would reintroduce incorrect data."""
