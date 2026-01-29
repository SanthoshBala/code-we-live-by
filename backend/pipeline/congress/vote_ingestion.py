"""Ingest vote data from Congress.gov into the database."""

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataIngestionLog, IndividualVote, Legislator, Vote
from app.models.enums import Chamber, VoteType
from pipeline.congress.client import CongressClient, HouseVoteDetail, MemberVoteInfo

logger = logging.getLogger(__name__)


def _parse_vote_date(date_str: str | None) -> date:
    """Parse vote date string to date object.

    Args:
        date_str: Date string from API (e.g., "2024-01-15").

    Returns:
        Parsed date or epoch date if parsing fails.
    """
    if not date_str:
        return date(1970, 1, 1)
    try:
        # Handle various date formats
        if "T" in date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return date(1970, 1, 1)


def _parse_vote_cast(vote_position: str) -> VoteType:
    """Convert vote position string to VoteType enum.

    Args:
        vote_position: Vote position from API (e.g., "Yea", "Nay").

    Returns:
        VoteType enum value.
    """
    position_lower = vote_position.lower().strip()

    if position_lower in ("yea", "aye", "yes"):
        return VoteType.YEA
    elif position_lower in ("nay", "no"):
        return VoteType.NAY
    elif position_lower == "present":
        return VoteType.PRESENT
    elif position_lower in ("not voting", "not_voting", "notvoting"):
        return VoteType.NOT_VOTING
    elif "paired" in position_lower and "yea" in position_lower:
        return VoteType.PAIRED_YEA
    elif "paired" in position_lower and "nay" in position_lower:
        return VoteType.PAIRED_NAY
    else:
        # Default to not voting for unknown values
        logger.warning(f"Unknown vote position: {vote_position}")
        return VoteType.NOT_VOTING


class VoteIngestionService:
    """Service for ingesting vote data into the database."""

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

    async def ingest_house_vote(
        self,
        congress: int,
        session_num: int,
        roll_number: int,
        force: bool = False,
    ) -> DataIngestionLog:
        """Ingest a single House roll call vote.

        Args:
            congress: Congress number (118+).
            session_num: Session number (1 or 2).
            roll_number: Roll call vote number.
            force: If True, update existing record.

        Returns:
            Ingestion log record.
        """
        log = DataIngestionLog(
            source="Congress.gov",
            operation=f"ingest_house_vote_{congress}_{session_num}_{roll_number}",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.session.add(log)
        await self.session.flush()

        try:
            # Fetch vote detail
            detail = await self.client.get_house_vote_detail(
                congress, session_num, roll_number
            )

            # Check for existing vote
            result = await self.session.execute(
                select(Vote).where(
                    Vote.chamber == Chamber.HOUSE,
                    Vote.congress == congress,
                    Vote.session == session_num,
                    Vote.vote_number == roll_number,
                )
            )
            existing = result.scalar_one_or_none()

            if existing and not force:
                log.status = "completed"
                log.completed_at = datetime.utcnow()
                log.records_processed = 1
                log.records_created = 0
                log.records_updated = 0
                log.details = (
                    f"Skipped (exists): House {congress}/{session_num}/{roll_number}"
                )
                await self.session.commit()
                return log

            # Fetch member votes
            member_votes = await self.client.get_house_vote_members(
                congress, session_num, roll_number
            )

            # Create or update vote record
            was_created = await self._upsert_vote(detail, member_votes, existing)

            log.status = "completed"
            log.completed_at = datetime.utcnow()
            log.records_processed = 1
            log.records_created = 1 if was_created else 0
            log.records_updated = 0 if was_created else 1
            log.details = (
                f"House {congress}/{session_num}/{roll_number}: {detail.result}"
            )

            await self.session.commit()
            return log

        except Exception as e:
            logger.exception(
                f"Error ingesting House vote {congress}/{session_num}/{roll_number}"
            )
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            await self.session.rollback()
            self.session.add(log)
            await self.session.commit()
            return log

    async def ingest_house_votes_for_congress(
        self,
        congress: int,
        session_num: int | None = None,
        force: bool = False,
        limit: int | None = None,
    ) -> DataIngestionLog:
        """Ingest all House votes for a Congress (or session).

        Args:
            congress: Congress number (118+).
            session_num: Session number (1 or 2, optional).
            force: If True, update existing records.
            limit: Maximum votes to ingest (optional).

        Returns:
            Ingestion log record.
        """
        session_str = f"/{session_num}" if session_num else ""
        log = DataIngestionLog(
            source="Congress.gov",
            operation=f"ingest_house_votes_{congress}{session_str}",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.session.add(log)
        await self.session.flush()

        try:
            # Fetch list of votes
            votes = await self.client.get_house_votes(
                congress, session=session_num, limit=limit
            )
            logger.info(
                f"Found {len(votes)} House votes for Congress {congress}{session_str}"
            )

            created = 0
            updated = 0
            skipped = 0

            for vote_info in votes:
                try:
                    # Get vote detail
                    detail = await self.client.get_house_vote_detail(
                        vote_info.congress, vote_info.session, vote_info.roll_number
                    )

                    # Check for existing
                    result = await self.session.execute(
                        select(Vote).where(
                            Vote.chamber == Chamber.HOUSE,
                            Vote.congress == vote_info.congress,
                            Vote.session == vote_info.session,
                            Vote.vote_number == vote_info.roll_number,
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing and not force:
                        skipped += 1
                        continue

                    # Get member votes
                    member_votes = await self.client.get_house_vote_members(
                        vote_info.congress, vote_info.session, vote_info.roll_number
                    )

                    was_created = await self._upsert_vote(
                        detail, member_votes, existing
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    logger.error(
                        f"Error ingesting vote {vote_info.congress}/{vote_info.session}/"
                        f"{vote_info.roll_number}: {e}"
                    )
                    continue

            log.status = "completed"
            log.completed_at = datetime.utcnow()
            log.records_processed = len(votes)
            log.records_created = created
            log.records_updated = updated
            log.details = (
                f"Congress {congress}{session_str}: {created} created, "
                f"{updated} updated, {skipped} skipped"
            )

            await self.session.commit()
            return log

        except Exception as e:
            logger.exception(f"Error ingesting House votes for Congress {congress}")
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            await self.session.rollback()
            self.session.add(log)
            await self.session.commit()
            return log

    async def _upsert_vote(
        self,
        detail: HouseVoteDetail,
        member_votes: list[MemberVoteInfo],
        existing: Vote | None,
    ) -> bool:
        """Insert or update a Vote record with individual votes.

        Args:
            detail: Vote detail from API.
            member_votes: List of member votes.
            existing: Existing vote record (if any).

        Returns:
            True if created, False if updated.
        """
        vote_date = _parse_vote_date(detail.vote_date)

        if existing:
            # Update existing vote
            existing.vote_date = vote_date
            existing.question = detail.question
            existing.result = detail.result
            existing.yeas = detail.yea_total
            existing.nays = detail.nay_total
            existing.present = detail.present_total
            existing.not_voting = detail.not_voting_total

            # Delete existing individual votes and re-add
            for iv in existing.individual_votes:
                await self.session.delete(iv)
            await self.session.flush()

            # Add individual votes
            await self._add_individual_votes(existing.vote_id, member_votes)
            return False

        # Create new vote
        vote = Vote(
            chamber=Chamber.HOUSE,
            congress=detail.congress,
            session=detail.session,
            vote_number=detail.roll_number,
            vote_date=vote_date,
            question=detail.question,
            result=detail.result,
            yeas=detail.yea_total,
            nays=detail.nay_total,
            present=detail.present_total,
            not_voting=detail.not_voting_total,
        )
        self.session.add(vote)
        await self.session.flush()

        # Add individual votes
        await self._add_individual_votes(vote.vote_id, member_votes)
        return True

    async def _add_individual_votes(
        self,
        vote_id: int,
        member_votes: list[MemberVoteInfo],
    ) -> int:
        """Add individual vote records for a vote.

        Args:
            vote_id: The Vote record ID.
            member_votes: List of member votes from API.

        Returns:
            Number of individual votes added.
        """
        added = 0
        for mv in member_votes:
            # Look up legislator by bioguide_id
            result = await self.session.execute(
                select(Legislator).where(Legislator.bioguide_id == mv.bioguide_id)
            )
            legislator = result.scalar_one_or_none()

            if not legislator:
                logger.debug(f"Legislator not found: {mv.bioguide_id} ({mv.name})")
                continue

            individual_vote = IndividualVote(
                vote_id=vote_id,
                legislator_id=legislator.legislator_id,
                vote_cast=_parse_vote_cast(mv.vote_cast),
            )
            self.session.add(individual_vote)
            added += 1

        return added
