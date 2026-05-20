"""Seed helpers for CODEOWNERS data: Committee rows and CommitteeUSCodeMapping rows."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.codeowners import CommitteeUSCodeMapping
from app.models.enums import Chamber
from app.models.supporting import Committee

logger = logging.getLogger(__name__)

_DEFAULT_COMMITTEE_YAML = Path(__file__).parent / "committee_seed.yaml"
_DEFAULT_MAPPING_YAML = Path(__file__).parent / "committee_usc_mappings.yaml"


async def seed_committees(
    session: AsyncSession,
    yaml_path: Path = _DEFAULT_COMMITTEE_YAML,
    force: bool = False,  # noqa: ARG001 — reserved for future selective update logic
) -> int:
    """Upsert Committee rows from a YAML fixture file.

    Returns the number of rows inserted or updated.
    Idempotent: safe to run multiple times.
    """
    data = yaml.safe_load(yaml_path.read_text())
    entries = data.get("committees", [])

    upserted = 0
    for entry in entries:
        code = entry["code"]
        chamber = Chamber(entry["chamber"])

        stmt = (
            insert(Committee)
            .values(
                committee_code=code,
                chamber=chamber,
                name=entry["name"],
                url=entry.get("url"),
                is_active=True,
            )
            .on_conflict_do_update(
                index_elements=["committee_code"],
                set_={
                    "name": entry["name"],
                    "url": entry.get("url"),
                    "is_active": True,
                },
            )
        )
        await session.execute(stmt)
        upserted += 1

    await session.commit()
    logger.info("Seeded %d committee rows from %s", upserted, yaml_path)
    return upserted


async def seed_codeowners_mappings(
    session: AsyncSession,
    yaml_path: Path = _DEFAULT_MAPPING_YAML,
    force: bool = False,  # noqa: ARG001 — reserved for future selective update logic
) -> int:
    """Upsert CommitteeUSCodeMapping rows from a YAML fixture file.

    Resolves committee_code → committee_id via the Committee table.
    Idempotent: safe to run multiple times. The Committee rows must
    exist before this is called (run seed_committees first).

    Returns the number of rows inserted or updated.
    """
    data = yaml.safe_load(yaml_path.read_text())
    entries = data.get("mappings", [])

    # Build a code → id lookup to avoid N+1 queries
    result = await session.execute(
        select(Committee.committee_code, Committee.committee_id)
    )
    code_to_id: dict[str, int] = {row[0]: row[1] for row in result}

    upserted = 0
    skipped = 0
    for entry in entries:
        code = entry["committee_code"]
        committee_id = code_to_id.get(code)
        if committee_id is None:
            logger.warning(
                "committee_code %r not found in Committee table — skipping mapping "
                "(title %s, ch. %s). Run seed-committees first.",
                code,
                entry["title_number"],
                entry.get("chapter_number"),
            )
            skipped += 1
            continue

        stmt = (
            insert(CommitteeUSCodeMapping)
            .values(
                committee_id=committee_id,
                congress_start=entry["congress_start"],
                congress_end=entry.get("congress_end"),
                title_number=entry["title_number"],
                chapter_number=entry.get("chapter_number"),
                jurisdiction_type=entry["jurisdiction_type"],
                display_order=entry.get("display_order", 0),
                notes=entry.get("notes"),
            )
            .on_conflict_do_update(
                constraint="uq_cum_committee_congress_path_type",
                set_={
                    "congress_end": entry.get("congress_end"),
                    "jurisdiction_type": entry["jurisdiction_type"],
                    "display_order": entry.get("display_order", 0),
                    "notes": entry.get("notes"),
                },
            )
        )
        await session.execute(stmt)
        upserted += 1

    await session.commit()
    logger.info(
        "Seeded %d CommitteeUSCodeMapping rows from %s (%d skipped)",
        upserted,
        yaml_path,
        skipped,
    )
    return upserted
