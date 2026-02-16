"""CRUD operations for the Law Viewer QC tool."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_law import PublicLaw
from app.schemas.law_viewer import (
    LawSummarySchema,
    LawTextSchema,
    ParsedAmendmentSchema,
    PositionQualifierSchema,
    SectionReferenceSchema,
)

logger = logging.getLogger(__name__)


async def get_laws_list(session: AsyncSession) -> list[LawSummarySchema]:
    """Return all public laws ordered by congress desc, law_number desc."""
    stmt = select(PublicLaw).order_by(
        PublicLaw.congress.desc(), PublicLaw.law_number.desc()
    )
    result = await session.execute(stmt)
    laws = result.scalars().all()

    return [
        LawSummarySchema(
            congress=law.congress,
            law_number=law.law_number,
            official_title=law.official_title,
            short_title=law.short_title,
            enacted_date=law.enacted_date.isoformat(),
            sections_affected=law.sections_affected,
        )
        for law in laws
    ]


def _date_str(d: Any) -> str | None:
    """Convert a date to ISO string, or None."""
    return d.isoformat() if d else None


async def get_law_text(
    session: AsyncSession, congress: int, law_number: int
) -> LawTextSchema | None:
    """Fetch raw HTM and XML text for a law, using cache or GovInfo API."""
    # Dynamic import to keep pipeline/ out of mypy's module graph
    try:
        govinfo_mod = importlib.import_module("pipeline.govinfo.client")
        client: Any = govinfo_mod.GovInfoClient()
    except (ValueError, ImportError):
        logger.warning("GovInfo API key not configured, reading from cache only")
        client = None

    htm_content: str | None = None
    xml_content: str | None = None

    if client:
        htm_content = await client.get_law_text(congress, law_number, format="htm")
        xml_content = await client.get_law_text(congress, law_number, format="xml")
    else:
        # Try reading from cache directly
        cache_dir = Path("data/govinfo/plaw")
        htm_file = cache_dir / f"PLAW-{congress}publ{law_number}.htm"
        xml_file = cache_dir / f"PLAW-{congress}publ{law_number}.xml"
        if htm_file.exists():
            htm_content = htm_file.read_text()
        if xml_file.exists():
            xml_content = xml_file.read_text()

    if htm_content is None and xml_content is None:
        return None

    # Query DB for metadata
    stmt = select(PublicLaw).where(
        PublicLaw.congress == congress,
        PublicLaw.law_number == str(law_number),
    )
    result = await session.execute(stmt)
    law = result.scalar_one_or_none()

    return LawTextSchema(
        congress=congress,
        law_number=str(law_number),
        official_title=law.official_title if law else None,
        short_title=law.short_title if law else None,
        enacted_date=_date_str(law.enacted_date) if law else None,
        introduced_date=_date_str(law.introduced_date) if law else None,
        house_passed_date=_date_str(law.house_passed_date) if law else None,
        senate_passed_date=_date_str(law.senate_passed_date) if law else None,
        presented_to_president_date=(
            _date_str(law.presented_to_president_date) if law else None
        ),
        effective_date=_date_str(law.effective_date) if law else None,
        htm_content=htm_content,
        xml_content=xml_content,
    )


def _amendment_to_schema(amendment: Any) -> ParsedAmendmentSchema:
    """Convert a ParsedAmendment dataclass to its API schema."""
    section_ref = None
    if amendment.section_ref:
        section_ref = SectionReferenceSchema(
            title=amendment.section_ref.title,
            section=amendment.section_ref.section,
            subsection_path=amendment.section_ref.subsection_path,
            display=str(amendment.section_ref),
        )

    position_qualifier = None
    if amendment.position_qualifier:
        position_qualifier = PositionQualifierSchema(
            type=amendment.position_qualifier.type.value,
            anchor_text=amendment.position_qualifier.anchor_text,
            target_text=amendment.position_qualifier.target_text,
        )

    return ParsedAmendmentSchema(
        pattern_name=amendment.pattern_name,
        pattern_type=amendment.pattern_type.value,
        change_type=amendment.change_type.value,
        section_ref=section_ref,
        old_text=amendment.old_text,
        new_text=amendment.new_text,
        full_match=amendment.full_match,
        confidence=amendment.confidence,
        needs_review=amendment.needs_review,
        context=amendment.context,
        position_qualifier=position_qualifier,
    )


async def parse_law_amendments(
    session: AsyncSession, congress: int, law_number: int
) -> list[ParsedAmendmentSchema]:
    """Parse amendments from a law's text on-the-fly for QC.

    Tries XML parsing first (higher fidelity), falls back to text parsing.
    """
    law_text = await get_law_text(session, congress, law_number)
    if not law_text:
        return []

    amendments: list[Any] = []

    # Dynamic imports to keep pipeline/ out of mypy's module graph
    if law_text.xml_content:
        try:
            xml_mod = importlib.import_module("pipeline.legal_parser.xml_parser")
            xml_parser = xml_mod.XMLAmendmentParser()
            amendments = xml_parser.parse(law_text.xml_content)
        except Exception:
            logger.exception(
                "XML parsing failed for PL %d-%d, falling back to text parser",
                congress,
                law_number,
            )
            amendments = []

    # Fall back to text parser if XML produced nothing
    if not amendments and law_text.htm_content:
        text_mod = importlib.import_module("pipeline.legal_parser.amendment_parser")
        text_parser = text_mod.AmendmentParser()
        amendments = text_parser.parse(law_text.htm_content)

    return [_amendment_to_schema(a) for a in amendments]
