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
from pipeline.olrc.group_service import _parse_citation_date

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(levelname)-5.5s [%(name)s] %(message)s"
)

BATCH_SIZE = 500


async def backfill(*, dry_run: bool = True) -> int:
    """Backfill last_modified_date from normalized_notes amendment citations.

    Prefers the full enactment date from amendment citations over the
    year-only approximation from the amendments list.

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
            if not notes:
                continue

            lmd: date | None = None

            # Prefer full date from non-Framework citations.  Including
            # Enactment citations covers sections enacted by a single law
            # with no subsequent amendments — the enactment date IS the
            # last-modified date.  Framework (pre-1957 structural context)
            # citations are excluded because their dates pre-date the
            # section's actual creation/modification.
            citations = notes.get("citations", [])
            modification_dates = []
            for c in citations:
                if c.get("relationship") == "Framework":
                    continue
                law_data = c.get("law") or c.get("act")
                if law_data and law_data.get("date"):
                    parsed = _parse_citation_date(law_data["date"])
                    if parsed is not None:
                        modification_dates.append(parsed)
            if modification_dates:
                lmd = max(modification_dates)
            else:
                # Fallback: year-only from amendments
                amendments = notes.get("amendments", [])
                years = [a.get("year") for a in amendments if a.get("year")]
                if years:
                    lmd = date(max(years), 1, 1)

            if lmd is None:
                continue

            batch.append({"sid": section_id, "lmd": lmd})

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
