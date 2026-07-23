"""Backfill renormalized notes[] list for sections with stale cached data.

Re-parses the raw ``notes`` text column and overwrites only the ``notes``
key inside the ``normalized_notes`` JSONB, leaving citations, amendments,
references, and other structured fields untouched.

Targets rows whose raw notes contain "References in Text", which is the note
type affected by two bug fixes applied after initial ingestion:

  1. ``subsecs.`` added to ``LEGAL_ABBREVIATIONS`` — stops false sentence
     splits at "subsecs." abbreviations.
  2. ``"References in Text"`` added to ``PARAGRAPH_LINE_HEADERS`` — routes
     that note type through ``_paragraph_lines()`` (one line per ``<p>``).

See GitHub issue #625.

Usage:
    uv run python -m pipeline.backfill_renormalize_notes          # dry-run
    uv run python -m pipeline.backfill_renormalize_notes --apply  # commit
"""

import asyncio
import json
import logging
import sys

from sqlalchemy import text

from app.models.base import async_session_maker
from pipeline.olrc.normalized_section import SectionNotes, _parse_notes_structure

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(levelname)-5.5s [%(name)s] %(message)s"
)

BATCH_SIZE = 100

# Tables that store (raw) notes + normalized_notes JSONB
_TABLES = [
    ("section_snapshot", "snapshot_id"),
    ("us_code_section", "section_id"),
]

_SELECT_SQL = """\
SELECT {pk}, notes, normalized_notes
FROM {table}
WHERE notes LIKE '%References in Text%'
  AND notes IS NOT NULL
  AND normalized_notes IS NOT NULL
ORDER BY {pk}
"""

_UPDATE_SQL = """\
UPDATE {table}
SET normalized_notes = jsonb_set(
        normalized_notes,
        '{{notes}}',
        :new_notes::jsonb
    )
WHERE {pk} = :row_id
"""


def _renormalize_notes_list(raw_notes: str) -> list[dict]:
    """Return the re-parsed notes[] list for the given raw notes text."""
    schema = SectionNotes()
    _parse_notes_structure(raw_notes, schema)
    return [note.model_dump(mode="json", exclude_none=True) for note in schema.notes]


async def _backfill_table(
    table: str,
    pk: str,
    *,
    dry_run: bool,
) -> int:
    """Backfill one table; return the number of rows that differ."""
    changed = 0

    async with async_session_maker() as session:
        result = await session.execute(text(_SELECT_SQL.format(table=table, pk=pk)))
        rows = result.all()
        logger.info("[%s] Found %d candidate rows", table, len(rows))

        batch: list[dict] = []

        for row_id, raw_notes, normalized_notes in rows:
            if not raw_notes or not normalized_notes:
                continue

            new_notes = _renormalize_notes_list(raw_notes)
            old_notes = normalized_notes.get("notes", [])

            # Compare serialised forms to detect any difference
            if json.dumps(new_notes, sort_keys=True) == json.dumps(
                old_notes, sort_keys=True
            ):
                continue

            batch.append(
                {
                    "row_id": row_id,
                    "new_notes": json.dumps(new_notes),
                }
            )

            if len(batch) >= BATCH_SIZE:
                if not dry_run:
                    for item in batch:
                        await session.execute(
                            text(_UPDATE_SQL.format(table=table, pk=pk)),
                            item,
                        )
                    await session.commit()
                changed += len(batch)
                logger.info("[%s] Processed %d changed rows so far", table, changed)
                batch = []

        # Final batch
        if batch:
            if not dry_run:
                for item in batch:
                    await session.execute(
                        text(_UPDATE_SQL.format(table=table, pk=pk)),
                        item,
                    )
                await session.commit()
            changed += len(batch)

    mode = "DRY-RUN" if dry_run else "APPLIED"
    logger.info("[%s][%s] %d rows would be updated", mode, table, changed)
    return changed


async def backfill(*, dry_run: bool = True) -> int:
    """Backfill stale notes[] in all affected tables.

    Returns the total number of rows updated (or that would be updated).
    """
    total = 0
    for table, pk in _TABLES:
        total += await _backfill_table(table, pk, dry_run=dry_run)

    mode = "DRY-RUN" if dry_run else "APPLIED"
    logger.info("[%s] Total rows affected: %d", mode, total)
    return total


def main() -> None:
    dry_run = "--apply" not in sys.argv
    if dry_run:
        logger.info("Running in dry-run mode (pass --apply to commit changes)")
    asyncio.run(backfill(dry_run=dry_run))


if __name__ == "__main__":
    main()
