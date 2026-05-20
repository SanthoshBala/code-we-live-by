"""Pydantic schemas for search API responses."""

from datetime import date

from pydantic import BaseModel


class SectionSearchResult(BaseModel):
    title_number: int
    section_number: str
    heading: str
    full_citation: str
    snippet: str | None = None
    is_repealed: bool = False
    last_modified_date: date | None = None


class LawSearchResult(BaseModel):
    congress: int
    law_number: str
    short_title: str | None = None
    popular_name: str | None = None
    enacted_date: date | None = None


class SectionSearchResponse(BaseModel):
    results: list[SectionSearchResult]
    total: int
    limit: int
    offset: int


class LawSearchResponse(BaseModel):
    results: list[LawSearchResult]
    total: int
    limit: int
    offset: int
