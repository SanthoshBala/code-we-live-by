"""Ingest legislator data from Congress.gov into the database."""

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataIngestionLog, Legislator, LegislatorTerm
from app.models.enums import Chamber, PoliticalParty
from pipeline.congress.client import CongressClient, MemberDetail, MemberTerm

logger = logging.getLogger(__name__)


def _parse_party(party_name: str | None) -> PoliticalParty | None:
    """Convert party name string to PoliticalParty enum.

    Args:
        party_name: Party name from API (e.g., "Democratic", "Republican").

    Returns:
        PoliticalParty enum value or None.
    """
    if not party_name:
        return None

    party_lower = party_name.lower()
    if "democrat" in party_lower:
        return PoliticalParty.DEMOCRAT
    elif "republican" in party_lower:
        return PoliticalParty.REPUBLICAN
    elif "independent" in party_lower:
        return PoliticalParty.INDEPENDENT
    elif "libertarian" in party_lower:
        return PoliticalParty.LIBERTARIAN
    elif "green" in party_lower:
        return PoliticalParty.GREEN
    else:
        return PoliticalParty.OTHER


def _parse_chamber(chamber_str: str) -> Chamber:
    """Convert chamber string to Chamber enum.

    Args:
        chamber_str: Chamber name from API (e.g., "House of Representatives", "Senate").

    Returns:
        Chamber enum value.
    """
    if "senate" in chamber_str.lower():
        return Chamber.SENATE
    return Chamber.HOUSE


def _year_to_date(year: int | None, month: int = 1, day: int = 1) -> date | None:
    """Convert year to date object.

    Args:
        year: Year as integer.
        month: Month (default January).
        day: Day (default 1st).

    Returns:
        Date object or None if year is None.
    """
    if year is None:
        return None
    return date(year, month, day)


class LegislatorIngestionService:
    """Service for ingesting legislator data into the database."""

    def __init__(
        self,
        session: AsyncSession,
        api_key: str | None = None,
    ):
        """Initialize the ingestion service.

        Args:
            session: SQLAlchemy async session.
            api_key: Congress.gov API key (or set CONGRESS_API_KEY env var).
        """
        self.session = session
        self.client = CongressClient(api_key=api_key)

    async def ingest_member(
        self,
        bioguide_id: str,
        force: bool = False,
    ) -> DataIngestionLog:
        """Ingest a single member of Congress.

        Args:
            bioguide_id: The member's Bioguide ID (e.g., "B000944").
            force: If True, update existing record.

        Returns:
            Ingestion log record.
        """
        log = DataIngestionLog(
            source="Congress.gov",
            operation=f"ingest_member_{bioguide_id}",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.session.add(log)
        await self.session.flush()

        try:
            detail = await self.client.get_member_detail(bioguide_id)
            was_created = await self._upsert_legislator(detail, force)

            log.status = "completed"
            log.completed_at = datetime.utcnow()
            log.records_processed = 1
            log.records_created = 1 if was_created is True else 0
            log.records_updated = 1 if was_created is False else 0
            log.details = f"{detail.direct_order_name} ({bioguide_id})"

            await self.session.commit()
            return log

        except Exception as e:
            logger.exception(f"Error ingesting member {bioguide_id}")
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            await self.session.rollback()
            self.session.add(log)
            await self.session.commit()
            return log

    async def ingest_congress(
        self,
        congress: int,
        force: bool = False,
    ) -> DataIngestionLog:
        """Ingest all members who served in a specific Congress.

        Args:
            congress: Congress number (e.g., 118).
            force: If True, update existing records.

        Returns:
            Ingestion log record.
        """
        log = DataIngestionLog(
            source="Congress.gov",
            operation=f"ingest_legislators_congress_{congress}",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.session.add(log)
        await self.session.flush()

        try:
            # Fetch member list for this Congress
            members = await self.client.get_members_by_congress(
                congress, current_member=False
            )
            logger.info(f"Found {len(members)} members for Congress {congress}")

            created = 0
            updated = 0
            skipped = 0

            for member_info in members:
                try:
                    # Get detailed info for each member
                    detail = await self.client.get_member_detail(
                        member_info.bioguide_id
                    )

                    # Upsert the legislator
                    was_created = await self._upsert_legislator(detail, force)
                    if was_created is True:
                        created += 1
                    elif was_created is False:
                        updated += 1
                    else:
                        skipped += 1

                except Exception as e:
                    logger.error(
                        f"Error ingesting member {member_info.bioguide_id}: {e}"
                    )
                    continue

            log.status = "completed"
            log.completed_at = datetime.utcnow()
            log.records_processed = len(members)
            log.records_created = created
            log.records_updated = updated
            log.details = (
                f"Congress {congress}: {created} created, "
                f"{updated} updated, {skipped} skipped"
            )

            await self.session.commit()
            return log

        except Exception as e:
            logger.exception(f"Error ingesting Congress {congress} members")
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            await self.session.rollback()
            self.session.add(log)
            await self.session.commit()
            return log

    async def ingest_current_members(
        self,
        force: bool = False,
    ) -> DataIngestionLog:
        """Ingest all currently serving members of Congress.

        Args:
            force: If True, update existing records.

        Returns:
            Ingestion log record.
        """
        log = DataIngestionLog(
            source="Congress.gov",
            operation="ingest_current_members",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.session.add(log)
        await self.session.flush()

        try:
            # Fetch all current members
            members = await self.client.get_members(current_member=True)
            logger.info(f"Found {len(members)} current members")

            created = 0
            updated = 0
            skipped = 0

            for member_info in members:
                try:
                    detail = await self.client.get_member_detail(
                        member_info.bioguide_id
                    )
                    was_created = await self._upsert_legislator(detail, force)
                    if was_created is True:
                        created += 1
                    elif was_created is False:
                        updated += 1
                    else:
                        skipped += 1
                except Exception as e:
                    logger.error(
                        f"Error ingesting member {member_info.bioguide_id}: {e}"
                    )
                    continue

            log.status = "completed"
            log.completed_at = datetime.utcnow()
            log.records_processed = len(members)
            log.records_created = created
            log.records_updated = updated
            log.details = f"Current members: {created} created, {updated} updated"

            await self.session.commit()
            return log

        except Exception as e:
            logger.exception("Error ingesting current members")
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            await self.session.rollback()
            self.session.add(log)
            await self.session.commit()
            return log

    async def _upsert_legislator(
        self,
        detail: MemberDetail,
        force: bool = False,
    ) -> bool | None:
        """Insert or update a Legislator record.

        Args:
            detail: Parsed member detail from Congress.gov.
            force: If True, update existing records.

        Returns:
            True if created, False if updated, None if skipped.
        """
        # Check for existing record
        result = await self.session.execute(
            select(Legislator).where(Legislator.bioguide_id == detail.bioguide_id)
        )
        existing = result.scalar_one_or_none()

        if existing and not force:
            return None  # Skipped

        # Parse party
        party = _parse_party(detail.party_name)

        # Determine current chamber from most recent term
        current_chamber: Chamber | None = None
        if detail.terms:
            # Sort terms by start year descending to get most recent
            sorted_terms = sorted(
                detail.terms,
                key=lambda t: t.start_year or 0,
                reverse=True,
            )
            if sorted_terms:
                current_chamber = _parse_chamber(sorted_terms[0].chamber)

        # Calculate first/last served dates from terms
        first_served: date | None = None
        last_served: date | None = None
        if detail.terms:
            start_years = [t.start_year for t in detail.terms if t.start_year]
            end_years = [t.end_year for t in detail.terms if t.end_year]
            if start_years:
                first_served = _year_to_date(min(start_years))
            if end_years:
                last_served = _year_to_date(max(end_years), 12, 31)
            elif detail.current_member and start_years:
                # Current member, no end year yet
                last_served = None

        # Extract state/district from most recent term
        state: str | None = detail.state
        district: str | None = None
        if detail.district is not None:
            district = str(detail.district)

        if existing:
            # Update existing record
            existing.first_name = detail.first_name
            existing.middle_name = detail.middle_name
            existing.last_name = detail.last_name
            existing.suffix = detail.suffix
            existing.full_name = detail.direct_order_name
            existing.party = party
            existing.state = state
            existing.district = district
            existing.current_chamber = current_chamber
            existing.is_current_member = detail.current_member
            existing.first_served = first_served
            existing.last_served = last_served
            existing.photo_url = detail.depiction_url
            existing.official_website = detail.official_website_url
            existing.birth_date = _year_to_date(detail.birth_year)
            existing.death_date = _year_to_date(detail.death_year)

            # Update terms
            await self._sync_terms(existing, detail.terms)

            return False  # Updated

        # Create new record
        legislator = Legislator(
            bioguide_id=detail.bioguide_id,
            first_name=detail.first_name,
            middle_name=detail.middle_name,
            last_name=detail.last_name,
            suffix=detail.suffix,
            full_name=detail.direct_order_name,
            party=party,
            state=state,
            district=district,
            current_chamber=current_chamber,
            is_current_member=detail.current_member,
            first_served=first_served,
            last_served=last_served,
            photo_url=detail.depiction_url,
            official_website=detail.official_website_url,
            birth_date=_year_to_date(detail.birth_year),
            death_date=_year_to_date(detail.death_year),
        )
        self.session.add(legislator)
        await self.session.flush()

        # Add terms
        await self._add_terms(legislator, detail.terms)

        return True  # Created

    async def _add_terms(
        self,
        legislator: Legislator,
        terms: list[MemberTerm],
    ) -> None:
        """Add terms for a legislator.

        Args:
            legislator: The Legislator record.
            terms: List of MemberTerm objects from the API.
        """
        for term in terms:
            if not term.start_year:
                continue

            term_record = LegislatorTerm(
                legislator_id=legislator.legislator_id,
                chamber=_parse_chamber(term.chamber),
                state=term.state or legislator.state or "XX",
                district=str(term.district) if term.district is not None else None,
                party=_parse_party(None) or PoliticalParty.OTHER,
                start_date=_year_to_date(term.start_year) or date(1970, 1, 1),
                end_date=(
                    _year_to_date(term.end_year, 12, 31) if term.end_year else None
                ),
                congress=term.congress,
            )
            self.session.add(term_record)

    async def _sync_terms(
        self,
        legislator: Legislator,
        terms: list[MemberTerm],
    ) -> None:
        """Sync terms for an existing legislator (delete and re-add).

        Args:
            legislator: The Legislator record.
            terms: List of MemberTerm objects from the API.
        """
        # Delete existing terms
        for existing_term in legislator.terms:
            await self.session.delete(existing_term)
        await self.session.flush()

        # Add new terms
        await self._add_terms(legislator, terms)
