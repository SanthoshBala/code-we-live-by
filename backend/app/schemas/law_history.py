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
        "amendment",
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
    amendment_status: str | None = None
    signing_statement: str | None = None
    signing_statement_url: str | None = None


class SponsorSchema(BaseModel):
    """A bill sponsor or cosponsor."""

    name: str
    party: str | None
    state: str | None
    district: int | None = None
    bioguide_id: str | None
    is_primary: bool


class ChamberVoteSchema(BaseModel):
    """Aggregated vote totals for one chamber's final passage vote."""

    chamber: str
    yeas: int
    nays: int
    not_voting: int


class AmendmentSchema(BaseModel):
    """An amendment to a bill."""

    amendment_number: str
    sponsor: str | None
    description: str | None
    purpose: str | None
    proposed_date: date | None
    action_date: date | None
    status: str | None


class CBOEstimateSchema(BaseModel):
    """A CBO cost estimate for a bill."""

    title: str
    url: str | None
    pub_date: date | None
    description: str | None


class RelatedBillSchema(BaseModel):
    """A bill related to this legislation."""

    congress: int
    bill_type: str
    bill_number: int
    title: str | None
    relationship_details: str | None
    law_number: int | None = None


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
    amendments: list[AmendmentSchema] = []
    cbo_estimates: list[CBOEstimateSchema] = []
    related_bills: list[RelatedBillSchema] = []
