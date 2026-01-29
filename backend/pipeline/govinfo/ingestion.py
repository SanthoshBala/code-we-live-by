"""Ingest Public Law data from GovInfo into the database."""

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataIngestionLog, PublicLaw
from app.models.enums import LawType
from pipeline.govinfo.client import GovInfoClient, PLAWPackageDetail

logger = logging.getLogger(__name__)


class PublicLawIngestionService:
    """Service for ingesting Public Law data into the database."""

    def __init__(
        self,
        session: AsyncSession,
        api_key: str | None = None,
    ):
        """Initialize the ingestion service.

        Args:
            session: SQLAlchemy async session.
            api_key: GovInfo API key (or set GOVINFO_API_KEY env var).
        """
        self.session = session
        self.client = GovInfoClient(api_key=api_key)

    async def ingest_congress(
        self,
        congress: int,
        force: bool = False,
    ) -> DataIngestionLog:
        """Ingest all Public Laws for a specific Congress.

        Args:
            congress: Congress number (e.g., 119).
            force: If True, update existing records.

        Returns:
            Ingestion log record.
        """
        log = DataIngestionLog(
            source="GovInfo",
            operation=f"ingest_congress_{congress}",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.session.add(log)
        await self.session.flush()

        try:
            # Fetch list of public laws for this Congress
            laws = await self.client.get_public_laws_for_congress(congress)
            logger.info(f"Found {len(laws)} public laws for Congress {congress}")

            created = 0
            updated = 0
            skipped = 0

            for law_info in laws:
                try:
                    # Get detailed info for each law
                    detail = await self.client.get_public_law_detail(
                        law_info.package_id
                    )

                    # Upsert the law
                    was_created = await self._upsert_public_law(detail, force)
                    if was_created is True:
                        created += 1
                    elif was_created is False:
                        updated += 1
                    else:
                        skipped += 1

                except Exception as e:
                    logger.error(f"Error ingesting {law_info.package_id}: {e}")
                    continue

            log.status = "completed"
            log.completed_at = datetime.utcnow()
            log.records_processed = len(laws)
            log.records_created = created
            log.records_updated = updated
            log.details = (
                f"Congress {congress}: {created} created, "
                f"{updated} updated, {skipped} skipped"
            )

            await self.session.commit()
            return log

        except Exception as e:
            logger.exception(f"Error ingesting Congress {congress}")
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            await self.session.rollback()
            self.session.add(log)
            await self.session.commit()
            return log

    async def ingest_law(
        self,
        congress: int,
        law_number: int,
        force: bool = False,
    ) -> DataIngestionLog:
        """Ingest a single Public Law.

        Args:
            congress: Congress number.
            law_number: Law number within that Congress.
            force: If True, update existing record.

        Returns:
            Ingestion log record.
        """
        package_id = self.client.build_package_id(congress, law_number)

        log = DataIngestionLog(
            source="GovInfo",
            operation=f"ingest_law_{congress}_{law_number}",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.session.add(log)
        await self.session.flush()

        try:
            detail = await self.client.get_public_law_detail(package_id)
            was_created = await self._upsert_public_law(detail, force)

            log.status = "completed"
            log.completed_at = datetime.utcnow()
            log.records_processed = 1
            log.records_created = 1 if was_created is True else 0
            log.records_updated = 1 if was_created is False else 0
            log.details = f"PL {congress}-{law_number}"

            await self.session.commit()
            return log

        except Exception as e:
            logger.exception(f"Error ingesting PL {congress}-{law_number}")
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            await self.session.rollback()
            self.session.add(log)
            await self.session.commit()
            return log

    async def ingest_recent_laws(
        self,
        days: int = 30,
        force: bool = False,
    ) -> DataIngestionLog:
        """Ingest Public Laws modified in the last N days.

        Args:
            days: Number of days to look back.
            force: If True, update existing records.

        Returns:
            Ingestion log record.
        """
        from datetime import timedelta

        start_date = datetime.utcnow() - timedelta(days=days)

        log = DataIngestionLog(
            source="GovInfo",
            operation=f"ingest_recent_laws_{days}d",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.session.add(log)
        await self.session.flush()

        try:
            laws = await self.client.get_public_laws(start_date=start_date)
            logger.info(f"Found {len(laws)} public laws modified in last {days} days")

            created = 0
            updated = 0
            skipped = 0

            for law_info in laws:
                try:
                    detail = await self.client.get_public_law_detail(
                        law_info.package_id
                    )
                    was_created = await self._upsert_public_law(detail, force)
                    if was_created is True:
                        created += 1
                    elif was_created is False:
                        updated += 1
                    else:
                        skipped += 1
                except Exception as e:
                    logger.error(f"Error ingesting {law_info.package_id}: {e}")
                    continue

            log.status = "completed"
            log.completed_at = datetime.utcnow()
            log.records_processed = len(laws)
            log.records_created = created
            log.records_updated = updated
            log.details = f"Last {days} days: {created} created, {updated} updated"

            await self.session.commit()
            return log

        except Exception as e:
            logger.exception("Error ingesting recent laws")
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            await self.session.rollback()
            self.session.add(log)
            await self.session.commit()
            return log

    async def _upsert_public_law(
        self,
        detail: PLAWPackageDetail,
        force: bool = False,
    ) -> bool | None:
        """Insert or update a Public Law record.

        Args:
            detail: Parsed law detail from GovInfo.
            force: If True, update existing records.

        Returns:
            True if created, False if updated, None if skipped.
        """
        # Check for existing record
        result = await self.session.execute(
            select(PublicLaw).where(
                PublicLaw.congress == detail.congress,
                PublicLaw.law_number == str(detail.law_number),
            )
        )
        existing = result.scalar_one_or_none()

        if existing and not force:
            return None  # Skipped

        # Determine law type
        law_type = LawType.PUBLIC if detail.law_type == "public" else LawType.PRIVATE

        # Convert date_issued to date
        enacted_date: date
        if detail.date_issued:
            enacted_date = detail.date_issued.date()
        else:
            # Use a placeholder date if not available
            enacted_date = date(1970, 1, 1)

        # Build GovInfo URL
        govinfo_url = f"https://www.govinfo.gov/app/details/{detail.package_id}"

        if existing:
            # Update existing record
            existing.law_type = law_type
            existing.official_title = detail.title
            existing.enacted_date = enacted_date
            existing.govinfo_url = govinfo_url
            existing.statutes_at_large_citation = detail.statutes_at_large_citation
            return False  # Updated

        # Create new record
        law = PublicLaw(
            law_number=str(detail.law_number),
            congress=detail.congress,
            law_type=law_type,
            official_title=detail.title,
            enacted_date=enacted_date,
            govinfo_url=govinfo_url,
            statutes_at_large_citation=detail.statutes_at_large_citation,
        )
        self.session.add(law)
        await self.session.flush()
        return True  # Created
