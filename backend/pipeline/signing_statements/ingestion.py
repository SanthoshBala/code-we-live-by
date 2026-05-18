"""DB ingestion service for presidential signing statements.

Fetches signing statement text from GovInfo CPD and persists it on the
PublicLaw row so the History tab can display it without a live API call
on every request.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_law import PublicLaw
from pipeline.signing_statements.fetcher import fetch_signing_statement

logger = logging.getLogger(__name__)


class SigningStatementIngestionService:
    """Fetches and persists signing statements for public laws."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def seed_law(
        self,
        congress: int,
        law_number: int,
        force: bool = False,
    ) -> bool:
        """Fetch and store the signing statement for a single law.

        Args:
            congress: Congress number (e.g. 118).
            law_number: Public law number (e.g. 5).
            force: Overwrite an existing statement if one is already stored.

        Returns:
            True if a statement was found and stored, False otherwise.
        """
        stmt = select(PublicLaw).where(
            PublicLaw.congress == congress,
            PublicLaw.law_number == str(law_number),
        )
        result = await self.session.execute(stmt)
        law: PublicLaw | None = result.scalar_one_or_none()

        if law is None:
            logger.warning("Law PL %d-%d not found in database", congress, law_number)
            return False

        if law.signing_statement and not force:
            logger.debug(
                "Signing statement for PL %d-%d already stored; skipping",
                congress,
                law_number,
            )
            return True

        title = law.short_title or law.popular_name or law.official_title or ""
        fetched = await fetch_signing_statement(congress, str(law_number), title=title)
        if fetched is None:
            return False

        law.signing_statement = fetched.text
        law.signing_statement_url = fetched.source_url
        await self.session.flush()
        logger.info(
            "Stored signing statement for PL %d-%d (%s)",
            congress,
            law_number,
            fetched.source_url,
        )
        return True

    async def seed_congress(
        self,
        congress: int,
        force: bool = False,
    ) -> tuple[int, int]:
        """Seed signing statements for all laws in a congress.

        Returns:
            (found_count, total_count) tuple.
        """
        stmt = select(PublicLaw).where(PublicLaw.congress == congress)
        result = await self.session.execute(stmt)
        laws = result.scalars().all()

        found = 0
        for law in laws:
            try:
                law_num = int(law.law_number)
            except (ValueError, TypeError):
                continue
            stored = await self.seed_law(congress, law_num, force=force)
            if stored:
                found += 1

        await self.session.commit()
        logger.info(
            "Signing statement seed complete for congress %d: %d/%d laws have statements",
            congress,
            found,
            len(laws),
        )
        return found, len(laws)
