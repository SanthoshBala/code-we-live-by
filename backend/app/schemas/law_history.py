"""Pydantic schemas for the legislative history API endpoint."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel


class TimelineEventSchema(BaseModel):
    """A single event in a bill's legislative timeline."""

    event_type: Literal[
        "introduced",
        "committee_referral",
        "house_vote",
        "senate_vote",
        "presidential_action",
        "other",
    ]
    date: date | None
    title: str
    description: str
    chamber: str | None
    is_milestone: bool
    vote_yeas: int | None = None
    vote_nays: int | None = None
    vote_not_voting: int | None = None
    congressional_record_refs: list[str] = []


class SponsorSchema(BaseModel):
    """A bill sponsor or cosponsor."""

    name: str
    party: str | None
    state: str | None
    bioguide_id: str | None
    is_primary: bool


class ChamberVoteSchema(BaseModel):
    """Aggregated vote totals for one chamber's final passage vote."""

    chamber: str
    yeas: int
    nays: int
    not_voting: int


class LegislativeHistorySchema(BaseModel):
    """Full legislative history response for a public law."""

    timeline: list[TimelineEventSchema]
    sponsors: list[SponsorSchema]
    chamber_votes: list[ChamberVoteSchema]
    presidential_action: str | None  # "signed", "vetoed", "pocket_vetoed", etc.
    president_name: str | None
    enacted_date: date | None
    status: Literal["enacted", "vetoed", "pending"]
    congress_url: str | None
