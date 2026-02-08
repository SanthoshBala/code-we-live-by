"""Backfill last_modified_date on sections from normalized_notes amendments.

Usage:
    uv run python -m pipeline.backfill_last_modified          # dry-run
    uv run python -m pipeline.backfill_last_modified --apply  # commit changes
"""

import asyncio
import logging
import sys
from datetime import date

from sqlalchemy import select, update

from app.models.base import async_session_maker
from app.models.us_code import USCodeSection

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(levelname)-5.5s [%(name)s] %(message)s"
)

BATCH_SIZE = 500


async def backfill(*, dry_run: bool = True) -> int:
    """Backfill last_modified_date from normalized_notes amendments.

    Returns the number of rows updated.
    """
    updated = 0

    async with async_session_maker() as session:
        # Select sections with notes but no last_modified_date
        stmt = select(
            USCodeSection.section_id,
            USCodeSection.normalized_notes,
        ).where(
            USCodeSection.last_modified_date.is_(None),
            USCodeSection.normalized_notes.isnot(None),
        )
        result = await session.execute(stmt)
        rows = result.all()

        logger.info("Found %d sections to check", len(rows))

        batch: list[dict] = []
        for section_id, notes in rows:
            amendments = notes.get("amendments", []) if notes else []
            if not amendments:
                continue

            years = [a.get("year") for a in amendments if a.get("year")]
            if not years:
                continue

            max_year = max(years)
            batch.append({"sid": section_id, "lmd": date(max_year, 1, 1)})

            if len(batch) >= BATCH_SIZE:
                if not dry_run:
                    for item in batch:
                        await session.execute(
                            update(USCodeSection)
                            .where(USCodeSection.section_id == item["sid"])
                            .values(last_modified_date=item["lmd"])
                        )
                    await session.commit()
                updated += len(batch)
                logger.info("Processed %d rows so far", updated)
                batch = []

        # Final batch
        if batch:
            if not dry_run:
                for item in batch:
                    await session.execute(
                        update(USCodeSection)
                        .where(USCodeSection.section_id == item["sid"])
                        .values(last_modified_date=item["lmd"])
                    )
                await session.commit()
            updated += len(batch)

    mode = "DRY-RUN" if dry_run else "APPLIED"
    logger.info("[%s] Would update %d sections", mode, updated)
    return updated


def main() -> None:
    dry_run = "--apply" not in sys.argv
    if dry_run:
        logger.info("Running in dry-run mode (pass --apply to commit)")
    asyncio.run(backfill(dry_run=dry_run))


if __name__ == "__main__":
    main()
