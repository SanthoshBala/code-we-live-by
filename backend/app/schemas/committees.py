"""Pydantic schemas for CODEOWNERS committee endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class CommitteeBaseSchema(BaseModel):
    committee_code: str
    chamber: str
    name: str
    url: str | None


class CommitteeOwnershipSchema(BaseModel):
    committee: CommitteeBaseSchema
    jurisdiction_type: str
    display_order: int
    title_number: int
    chapter_number: str | None
    notes: str | None
    congress_start: int
    congress_end: int | None


class CodeOwnersForPathSchema(BaseModel):
    title_number: int
    chapter_number: str | None
    congress: int
    owners: list[CommitteeOwnershipSchema]


class CommitteeCongressInstanceSchema(BaseModel):
    committee_code: str
    chamber: str
    official_name: str
    congress: int
    rule_citation: str | None
