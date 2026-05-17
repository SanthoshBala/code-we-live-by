"""Pipeline service for seeding legislative history into the DB.

Fetches bill actions and sponsors from Congress.gov and stores them in the
law_bill_action and law_sponsor tables so the History tab can serve responses
from the DB instead of hitting the live API on every request.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.law_history_helpers import (
    build_event_title,
    classify_action,
    parse_vote_tally,
)
from app.models.public_law import LawBillAction, LawSponsor, PublicLaw
from app.models.supporting import DataIngestionLog

if TYPE_CHECKING:
    from pipeline.cache import PipelineCache

logger = logging.getLogger(__name__)


class LawHistoryIngestionService:
    """Fetches and persists legislative history (actions + sponsors) for public laws."""

    def __init__(
        self,
        session: AsyncSession,
        cache: PipelineCache | None = None,
    ) -> None:
        self.session = session
        self.cache = cache

    async def seed_law(
        self,
        congress: int,
        law_number: int,
        force: bool = False,
    ) -> DataIngestionLog:
        """Seed bill actions and sponsors for a single law.

        Args:
            congress: Congress number (e.g. 117).
            law_number: Public law number (e.g. 169).
            force: If True, delete existing rows and re-fetch.

        Returns:
            DataIngestionLog with status and counts.
        """
        log = DataIngestionLog(
            source="Congress.gov",
            operation=f"seed-law-history-{congress}-{law_number}",
            status="started",
            records_processed=0,
            records_created=0,
            records_updated=0,
        )
        self.session.add(log)

        try:
            law = await self._fetch_law(congress, law_number)
            if law is None:
                log.status = "failed"
                log.error_message = f"Law PL {congress}-{law_number} not found in DB"
                await self.session.commit()
                return log

            # Skip if already seeded and not forced
            if not force:
                existing = await self._count_existing(law.law_id)
                if existing > 0:
                    log.status = "skipped"
                    log.details = (
                        f"Already seeded ({existing} actions). Use --force to re-seed."
                    )
                    await self.session.commit()
                    return log

            congress_client = self._make_client()
            if congress_client is None:
                log.status = "failed"
                log.error_message = "Congress.gov API key not configured"
                await self.session.commit()
                return log

            bill_ref = await self._resolve_bill_ref(law, congress_client)
            if bill_ref is None:
                log.status = "failed"
                log.error_message = (
                    f"Could not resolve bill reference for PL {congress}-{law_number}"
                )
                await self.session.commit()
                return log

            bill_type, bill_number_int = bill_ref

            # Delete existing rows if forcing
            if force:
                await self.session.execute(
                    delete(LawBillAction).where(LawBillAction.law_id == law.law_id)
                )
                await self.session.execute(
                    delete(LawSponsor).where(LawSponsor.law_id == law.law_id)
                )

            actions_created = await self._ingest_actions(
                law.law_id, congress, bill_type, bill_number_int, congress_client
            )
            sponsors_created = await self._ingest_sponsors(
                law.law_id, congress, bill_type, bill_number_int, congress_client
            )

            total = actions_created + sponsors_created
            log.status = "completed"
            log.records_processed = total
            log.records_created = total
            log.details = f"{actions_created} actions, {sponsors_created} sponsors"
            await self.session.commit()

        except Exception as exc:
            await self.session.rollback()
            log.status = "failed"
            log.error_message = str(exc)
            logger.exception(
                "Failed to seed law history for PL %d-%d", congress, law_number
            )
            self.session.add(log)
            await self.session.commit()

        return log

    async def seed_congress(
        self,
        congress: int,
        force: bool = False,
    ) -> DataIngestionLog:
        """Seed bill actions and sponsors for all laws in a congress.

        Args:
            congress: Congress number.
            force: If True, re-seed even if data already exists.

        Returns:
            Aggregate DataIngestionLog.
        """
        log = DataIngestionLog(
            source="Congress.gov",
            operation=f"seed-congress-law-history-{congress}",
            status="started",
            records_processed=0,
            records_created=0,
            records_updated=0,
        )
        self.session.add(log)
        await self.session.flush()

        stmt = select(PublicLaw).where(PublicLaw.congress == congress)
        result = await self.session.execute(stmt)
        laws = result.scalars().all()

        total_created = 0
        total_processed = 0
        failed = 0
        failure_reasons: list[str] = []

        for law in laws:
            child_log = await self.seed_law(
                law.congress, int(law.law_number), force=force
            )
            total_processed += child_log.records_processed or 0
            total_created += child_log.records_created or 0
            if child_log.status == "failed":
                failed += 1
                reason = child_log.error_message or "unknown error"
                failure_reasons.append(f"PL {law.congress}-{law.law_number}: {reason}")
                logger.warning(
                    "Failed to seed PL %d-%s: %s",
                    law.congress,
                    law.law_number,
                    reason,
                )

        log.status = "failed" if failed > 0 and total_created == 0 else "completed"
        log.records_processed = total_processed
        log.records_created = total_created
        log.details = (
            f"{len(laws)} laws processed, {failed} failed, {total_created} rows created"
        )
        if log.status == "failed" and failure_reasons:
            # Surface the first reason so callers get a useful message rather than None
            first = failure_reasons[0]
            summary = f"{failed}/{len(laws)} laws failed — first: {first}"
            log.error_message = summary
        await self.session.commit()
        return log

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_law(self, congress: int, law_number: int) -> PublicLaw | None:
        stmt = (
            select(PublicLaw)
            .where(
                PublicLaw.congress == congress,
                PublicLaw.law_number == str(law_number),
            )
            .options(selectinload(PublicLaw.origin_bill))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _count_existing(self, law_id: int) -> int:
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(LawBillAction)
            .where(LawBillAction.law_id == law_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    def _make_client(self) -> Any | None:
        import importlib

        try:
            mod = importlib.import_module("pipeline.congress.client")
            return mod.CongressClient(cache=self.cache)
        except (ValueError, ImportError) as exc:
            logger.warning("Congress.gov API unavailable: %s", exc)
            return None

    async def _resolve_bill_ref(
        self, law: PublicLaw, congress_client: Any
    ) -> tuple[str, int] | None:
        """Return (bill_type_lower, bill_number_int) or None."""
        bill = law.origin_bill
        if bill is not None and bill.bill_number:
            bill_type = bill.bill_type.value.lower()
            try:
                return bill_type, int(bill.bill_number)
            except ValueError:
                pass

        try:
            law_number_int = int(law.law_number)
            data = await congress_client.get_law_bill_info(
                law.congress, law_number_int, "pub"
            )
        except Exception as exc:
            logger.warning(
                "get_law_bill_info failed for PL %s-%s: %s",
                law.congress,
                law.law_number,
                exc,
            )
            return None

        if data is None:
            return None

        congress_data = data.get("congress", {})
        bills = congress_data.get("bills", [])
        if not bills:
            return None
        bill_ref = bills[0]
        b_type = (bill_ref.get("type") or "").lower()
        b_number = bill_ref.get("number")
        if not b_type or not b_number:
            return None
        try:
            return b_type, int(b_number)
        except (ValueError, TypeError):
            return None

    async def _ingest_actions(
        self,
        law_id: int,
        congress: int,
        bill_type: str,
        bill_number: int,
        congress_client: Any,
    ) -> int:
        try:
            raw_actions = await congress_client.get_bill_actions(
                congress, bill_type, bill_number
            )
        except Exception as exc:
            logger.warning("Failed to fetch bill actions: %s", exc)
            return 0

        seen_intro = False
        seen_committee = False
        created = 0

        for sort_order, action in enumerate(raw_actions):
            event_type, is_milestone = classify_action(
                action.action_type,
                action.text,
                action.chamber,
                seen_intro,
                seen_committee,
            )

            if event_type == "introduced":
                seen_intro = True
            if event_type == "committee_referral":
                seen_committee = True

            yeas, nays, not_voting = parse_vote_tally(action.text)
            title = build_event_title(event_type, action.text, action.chamber)

            row = LawBillAction(
                law_id=law_id,
                sort_order=sort_order,
                action_date=action.action_date,
                action_code=action.action_code,
                action_type=action.action_type,
                text=action.text,
                chamber=action.chamber,
                congressional_record_refs=action.congressional_record_refs,
                event_type=event_type,
                is_milestone=is_milestone,
                vote_yeas=yeas,
                vote_nays=nays,
                vote_not_voting=not_voting,
                event_title=title,
            )
            self.session.add(row)
            created += 1

        return created

    async def _ingest_sponsors(
        self,
        law_id: int,
        congress: int,
        bill_type: str,
        bill_number: int,
        congress_client: Any,
    ) -> int:
        try:
            sponsor_info, cosponsors = await congress_client.get_bill_sponsors(
                congress, bill_type, bill_number
            )
        except Exception as exc:
            logger.warning("Failed to fetch sponsors: %s", exc)
            return 0

        created = 0
        sort_order = 0

        if sponsor_info:
            row = LawSponsor(
                law_id=law_id,
                sort_order=sort_order,
                name=sponsor_info.full_name,
                party=sponsor_info.party,
                state=sponsor_info.state,
                bioguide_id=sponsor_info.bioguide_id,
                is_primary=True,
            )
            self.session.add(row)
            created += 1
            sort_order += 1

        for cs in cosponsors:
            row = LawSponsor(
                law_id=law_id,
                sort_order=sort_order,
                name=cs.full_name,
                party=cs.party,
                state=cs.state,
                bioguide_id=cs.bioguide_id,
                is_primary=False,
            )
            self.session.add(row)
            created += 1
            sort_order += 1

        return created
