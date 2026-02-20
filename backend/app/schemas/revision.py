"""Pydantic schemas for revision endpoints."""

from datetime import date

from pydantic import BaseModel


class HeadRevisionSchema(BaseModel):
    """Schema for the HEAD (latest ingested) revision."""

    revision_id: int
    revision_type: str
    effective_date: date
    summary: str | None
    sequence_number: int

    model_config = {"from_attributes": True}
