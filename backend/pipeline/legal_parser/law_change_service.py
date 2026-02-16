"""Law change service — orchestrator for processing a Public Law into LawChange records.

This is the main entry point for converting a parsed law into structured change
records. It coordinates:
1. Fetching and parsing law text
2. Resolving section references
3. Extracting following text for add/insert patterns
4. Generating validated diffs
5. Persisting LawChange records
6. Updating PublicLaw statistics
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataIngestionLog
from app.models.public_law import LawChange, PublicLaw
from pipeline.govinfo.client import GovInfoClient
from pipeline.legal_parser.amendment_parser import ParsedAmendment
from pipeline.legal_parser.diff_generator import DiffGenerator, DiffReport, DiffResult
from pipeline.legal_parser.parsing_modes import RegExParsingSession
from pipeline.legal_parser.section_resolver import SectionResolver
from pipeline.legal_parser.text_extractor import TextExtractor

logger = logging.getLogger(__name__)


@dataclass
class LawChangeResult:
    """Result of processing a law for changes.

    Attributes:
        law: The PublicLaw record.
        amendments: Parsed amendments from the law text.
        diffs: Generated diff results.
        report: Diff generation report.
        changes: Persisted LawChange records.
        errors: Any errors encountered.
        dry_run: Whether this was a dry run (no persistence).
    """

    law: PublicLaw
    amendments: list[ParsedAmendment] = field(default_factory=list)
    diffs: list[DiffResult] = field(default_factory=list)
    report: DiffReport | None = None
    changes: list[LawChange] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False


class LawChangeService:
    """Orchestrate the full pipeline for processing a law into LawChange records.

    This service coordinates all the steps needed to convert a Public Law's text
    into structured change records in the database.
    """

    def __init__(
        self,
        session: AsyncSession,
        govinfo_client: GovInfoClient | None = None,
    ):
        self.session = session
        self.govinfo_client = govinfo_client

    async def process_law(
        self,
        congress: int,
        law_number: int,
        default_title: int | None = None,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> LawChangeResult:
        """Process a Public Law to generate LawChange records.

        This is the main orchestration method that:
        1. Fetches law text from GovInfo
        2. Parses amendments (using RegExParsingSession)
        3. Resolves section references to database records
        4. Extracts "the following" text for ADD/INSERT patterns
        5. Generates validated diffs
        6. Persists LawChange records (unless dry_run)
        7. Updates PublicLaw statistics

        Args:
            congress: Congress number (e.g., 113).
            law_number: Law number (e.g., 22).
            default_title: Default US Code title for amendments that don't specify.
            dry_run: If True, generate diffs without persisting.
            verbose: If True, log detailed progress.

        Returns:
            LawChangeResult with all processing details.
        """
        # Step 1: Find the law in the database
        law_result = await self.session.execute(
            select(PublicLaw).where(
                PublicLaw.congress == congress,
                PublicLaw.law_number == str(law_number),
            )
        )
        law = law_result.scalar_one_or_none()

        if not law:
            result = LawChangeResult(
                law=PublicLaw(congress=congress, law_number=str(law_number)),
                dry_run=dry_run,
            )
            result.errors.append(
                f"PL {congress}-{law_number} not in database. "
                "Run 'govinfo-ingest-law' first."
            )
            return result

        result = LawChangeResult(law=law, dry_run=dry_run)

        # Create ingestion log
        log = DataIngestionLog(
            source="LawChangeService",
            operation=f"process_law_{congress}_{law_number}",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.session.add(log)
        await self.session.flush()

        try:
            # Step 2: Fetch law text
            client = self.govinfo_client or GovInfoClient()
            law_text = await client.get_law_text(congress, law_number)
            if not law_text:
                result.errors.append(
                    f"Could not retrieve text for PL {congress}-{law_number}"
                )
                log.status = "failed"
                log.error_message = "Law text not available"
                log.completed_at = datetime.utcnow()
                await self.session.commit()
                return result

            if verbose:
                logger.info(
                    f"Processing PL {congress}-{law_number} "
                    f"({len(law_text):,} chars)"
                )

            # Step 3: Parse amendments
            parser_session = RegExParsingSession(
                self.session,
                default_title=default_title,
            )
            parse_result = await parser_session.parse_law(
                law_id=law.law_id,
                law_text=law_text,
                save_to_db=not dry_run,
            )
            result.amendments = parse_result.amendments

            if verbose:
                logger.info(f"  Found {len(result.amendments)} amendments")

            if not result.amendments:
                log.status = "completed"
                log.completed_at = datetime.utcnow()
                log.details = "No amendments found"
                await self.session.commit()
                return result

            # Step 4: Resolve section references
            resolver = SectionResolver(self.session)
            section_refs = [a.section_ref for a in result.amendments]
            resolutions = await resolver.resolve_batch(
                [ref for ref in section_refs if ref is not None],
                default_title=default_title,
            )

            # Pad resolutions for amendments without section refs
            full_resolutions = []
            resolution_idx = 0
            for amendment in result.amendments:
                if amendment.section_ref is not None:
                    full_resolutions.append(resolutions[resolution_idx])
                    resolution_idx += 1
                else:
                    from pipeline.legal_parser.amendment_parser import SectionReference
                    from pipeline.legal_parser.section_resolver import ResolutionResult

                    full_resolutions.append(
                        ResolutionResult(
                            section_ref=SectionReference(title=None, section="?"),
                            error="No section reference in amendment",
                        )
                    )

            resolved_count = sum(1 for r in full_resolutions if r.resolved)
            if verbose:
                logger.info(
                    f"  Resolved {resolved_count}/{len(full_resolutions)} "
                    f"section references"
                )

            # Step 5: Extract following text
            extractor = TextExtractor(law_text)
            extractions = extractor.extract_batch(result.amendments)

            if verbose and extractions:
                logger.info(f"  Extracted text for {len(extractions)} amendments")

            # Step 6: Generate diffs
            diff_gen = DiffGenerator(self.session)
            diffs, report = await diff_gen.generate_diffs(
                result.amendments,
                full_resolutions,
                extractions,
                law,
            )
            result.diffs = diffs
            result.report = report

            if verbose:
                logger.info(
                    f"  Generated {report.diffs_generated} diffs "
                    f"({report.unresolved} unresolved, "
                    f"{report.diffs_skipped} skipped)"
                )

            # Step 7: Persist (unless dry run)
            if not dry_run:
                changes = await diff_gen.persist_law_changes(diffs, law)
                result.changes = changes

                # Update PublicLaw statistics
                await self._update_law_stats(law, report)

                await self.session.commit()

            log.status = "completed"
            log.completed_at = datetime.utcnow()
            log.records_processed = len(result.amendments)
            log.records_created = len(result.changes)
            log.details = (
                f"Amendments: {len(result.amendments)}, "
                f"Diffs: {report.diffs_generated}, "
                f"Changes: {len(result.changes)}"
            )

            if not dry_run:
                await self.session.commit()

            return result

        except Exception as e:
            logger.exception(f"Error processing PL {congress}-{law_number}")
            result.errors.append(str(e))
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            await self.session.rollback()
            self.session.add(log)
            await self.session.commit()
            return result

    async def _update_law_stats(self, law: PublicLaw, report: DiffReport) -> None:
        """Update PublicLaw aggregate statistics from diff report."""
        sections_added = 0
        sections_modified = 0
        sections_repealed = 0

        for type_name, count in report.by_type.items():
            if type_name == "Add":
                sections_added += count
            elif type_name in ("Modify", "Delete"):
                sections_modified += count
            elif type_name == "Repeal":
                sections_repealed += count

        law.sections_affected = report.diffs_generated
        law.sections_added = sections_added
        law.sections_modified = sections_modified
        law.sections_repealed = sections_repealed
