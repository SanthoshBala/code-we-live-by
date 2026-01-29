"""Tests for Congress.gov API client."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from pipeline.congress.client import (
    CongressClient,
    HouseVoteDetail,
    HouseVoteInfo,
    MemberDetail,
    MemberInfo,
    MemberTerm,
    MemberVoteInfo,
    SponsorInfo,
)


class TestMemberTerm:
    """Tests for MemberTerm dataclass."""

    def test_from_api_response_house(self) -> None:
        """Test parsing a House term from API response."""
        data = {
            "chamber": "House of Representatives",
            "congress": 118,
            "memberType": "Representative",
            "stateCode": "CA",
            "district": 12,
            "startYear": 2023,
            "endYear": 2025,
        }

        term = MemberTerm.from_api_response(data)

        assert term.chamber == "House of Representatives"
        assert term.congress == 118
        assert term.member_type == "Representative"
        assert term.state == "CA"
        assert term.district == 12
        assert term.start_year == 2023
        assert term.end_year == 2025

    def test_from_api_response_senate(self) -> None:
        """Test parsing a Senate term from API response."""
        data = {
            "chamber": "Senate",
            "congress": 118,
            "memberType": "Senator",
            "stateCode": "OH",
            "district": None,
            "startYear": 2007,
        }

        term = MemberTerm.from_api_response(data)

        assert term.chamber == "Senate"
        assert term.member_type == "Senator"
        assert term.state == "OH"
        assert term.district is None
        assert term.end_year is None


class TestMemberInfo:
    """Tests for MemberInfo dataclass."""

    def test_from_api_response_with_terms(self) -> None:
        """Test parsing member info with terms."""
        data = {
            "bioguideId": "B000944",
            "name": "Sherrod Brown",
            "state": "OH",
            "district": None,
            "partyName": "Democratic",
            "terms": {
                "item": [
                    {
                        "chamber": "Senate",
                        "congress": 118,
                        "memberType": "Senator",
                        "startYear": 2023,
                    }
                ]
            },
            "depiction": {
                "imageUrl": "https://www.congress.gov/img/member/b000944.jpg",
            },
        }

        info = MemberInfo.from_api_response(data)

        assert info.bioguide_id == "B000944"
        assert info.name == "Sherrod Brown"
        assert info.state == "OH"
        assert info.party_name == "Democratic"
        assert len(info.terms) == 1
        assert info.terms[0].chamber == "Senate"
        assert info.depiction_url == "https://www.congress.gov/img/member/b000944.jpg"

    def test_from_api_response_minimal(self) -> None:
        """Test parsing with minimal fields."""
        data = {
            "bioguideId": "S001145",
            "name": "Janice Schakowsky",
        }

        info = MemberInfo.from_api_response(data)

        assert info.bioguide_id == "S001145"
        assert info.name == "Janice Schakowsky"
        assert info.state is None
        assert info.party_name is None
        assert len(info.terms) == 0
        assert info.depiction_url is None


class TestMemberDetail:
    """Tests for MemberDetail dataclass."""

    def test_from_api_response_full(self) -> None:
        """Test parsing full member detail from API response."""
        data = {
            "bioguideId": "B000944",
            "firstName": "Sherrod",
            "middleName": None,
            "lastName": "Brown",
            "suffixName": None,
            "directOrderName": "Sherrod Brown",
            "invertedOrderName": "Brown, Sherrod",
            "honorificName": "Mr.",
            "partyName": "Democratic",
            "state": "OH",
            "district": None,
            "currentMember": True,
            "birthYear": 1952,
            "deathYear": None,
            "officialWebsiteUrl": "https://www.brown.senate.gov/",
            "depiction": {
                "imageUrl": "https://www.congress.gov/img/member/b000944.jpg",
                "attribution": "Image courtesy of the Member",
            },
            "terms": [
                {
                    "chamber": "Senate",
                    "congress": 118,
                    "memberType": "Senator",
                    "startYear": 2023,
                }
            ],
            "updateDate": "2024-01-15T10:30:00Z",
        }

        detail = MemberDetail.from_api_response(data)

        assert detail.bioguide_id == "B000944"
        assert detail.first_name == "Sherrod"
        assert detail.last_name == "Brown"
        assert detail.direct_order_name == "Sherrod Brown"
        assert detail.party_name == "Democratic"
        assert detail.state == "OH"
        assert detail.current_member is True
        assert detail.birth_year == 1952
        assert detail.death_year is None
        assert detail.official_website_url == "https://www.brown.senate.gov/"
        assert detail.depiction_url == "https://www.congress.gov/img/member/b000944.jpg"
        assert detail.depiction_attribution == "Image courtesy of the Member"
        assert len(detail.terms) == 1
        assert detail.update_date == datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

    def test_from_api_response_historical(self) -> None:
        """Test parsing a historical member (deceased)."""
        data = {
            "bioguideId": "K000009",
            "firstName": "Edward",
            "lastName": "Kennedy",
            "directOrderName": "Edward Kennedy",
            "invertedOrderName": "Kennedy, Edward",
            "partyName": "Democratic",
            "state": "MA",
            "currentMember": False,
            "birthYear": 1932,
            "deathYear": 2009,
            "terms": [],
        }

        detail = MemberDetail.from_api_response(data)

        assert detail.bioguide_id == "K000009"
        assert detail.first_name == "Edward"
        assert detail.last_name == "Kennedy"
        assert detail.current_member is False
        assert detail.birth_year == 1932
        assert detail.death_year == 2009


class TestSponsorInfo:
    """Tests for SponsorInfo dataclass."""

    def test_from_api_response_sponsor(self) -> None:
        """Test parsing sponsor info from API response."""
        data = {
            "bioguideId": "D000617",
            "fullName": "Rep. DelBene, Suzan K. [D-WA-1]",
            "firstName": "Suzan",
            "middleName": "K.",
            "lastName": "DelBene",
            "party": "D",
            "state": "WA",
            "district": 1,
        }

        sponsor = SponsorInfo.from_api_response(data)

        assert sponsor.bioguide_id == "D000617"
        assert sponsor.full_name == "Rep. DelBene, Suzan K. [D-WA-1]"
        assert sponsor.first_name == "Suzan"
        assert sponsor.last_name == "DelBene"
        assert sponsor.party == "D"
        assert sponsor.state == "WA"
        assert sponsor.district == 1

    def test_from_api_response_cosponsor(self) -> None:
        """Test parsing cosponsor info with sponsorship date."""
        data = {
            "bioguideId": "B001281",
            "fullName": "Rep. Beatty, Joyce [D-OH-3]",
            "firstName": "Joyce",
            "lastName": "Beatty",
            "party": "D",
            "state": "OH",
            "district": 3,
            "sponsorshipDate": "2021-05-06",
            "isOriginalCosponsor": True,
        }

        cosponsor = SponsorInfo.from_api_response(data)

        assert cosponsor.bioguide_id == "B001281"
        assert cosponsor.sponsorship_date == "2021-05-06"
        assert cosponsor.is_original_cosponsor is True


class TestCongressClient:
    """Tests for CongressClient class."""

    def test_init_requires_api_key(self) -> None:
        """Test that client requires an API key."""
        with patch("app.config.settings") as mock_settings:
            mock_settings.congress_api_key = None
            with pytest.raises(ValueError, match="API key required"):
                CongressClient()

    def test_init_with_api_key(self) -> None:
        """Test client initialization with API key."""
        client = CongressClient(api_key="test-key")

        assert client.api_key == "test-key"
        assert client.base_url == "https://api.congress.gov/v3"

    def test_init_with_timeout(self) -> None:
        """Test client initialization with custom timeout."""
        client = CongressClient(api_key="test-key", timeout=60.0)

        assert client.timeout == 60.0

    def test_retry_settings(self) -> None:
        """Test default retry settings."""
        client = CongressClient(api_key="test-key")

        assert client.max_retries == 3
        assert client.retry_delay == 2.0


class TestHouseVoteInfo:
    """Tests for HouseVoteInfo dataclass."""

    def test_from_api_response_basic(self) -> None:
        """Test parsing basic vote info from API response."""
        data = {
            "congress": 118,
            "sessionNumber": 1,
            "rollCallNumber": 100,
            "startDate": "2023-03-15T14:05:00-04:00",
            "voteType": "Recorded Vote",
            "result": "Passed",
        }

        info = HouseVoteInfo.from_api_response(data)

        assert info.congress == 118
        assert info.session == 1
        assert info.roll_number == 100
        assert info.vote_date == "2023-03-15T14:05:00-04:00"
        assert info.question == "Recorded Vote"
        assert info.result == "Passed"

    def test_from_api_response_with_bill(self) -> None:
        """Test parsing vote info with related bill."""
        data = {
            "congress": 118,
            "sessionNumber": 1,
            "rollCallNumber": 50,
            "startDate": "2023-02-01",
            "voteType": "On Passage",
            "result": "Passed",
            "legislationType": "HR",
            "legislationNumber": "123",
        }

        info = HouseVoteInfo.from_api_response(data)

        assert info.bill_type == "HR"
        assert info.bill_number == 123


class TestHouseVoteDetail:
    """Tests for HouseVoteDetail dataclass."""

    def test_from_api_response_full(self) -> None:
        """Test parsing full vote detail from API response."""
        data = {
            "houseRollCallVote": {
                "congress": 118,
                "sessionNumber": 1,
                "rollCallNumber": 100,
                "startDate": "2023-03-15T14:05:00-04:00",
                "voteType": "Recorded Vote",
                "voteQuestion": "On Passage",
                "result": "Passed",
                "votePartyTotal": [
                    {
                        "yeaTotal": 200,
                        "nayTotal": 10,
                        "presentTotal": 0,
                        "notVotingTotal": 2,
                    },
                    {
                        "yeaTotal": 17,
                        "nayTotal": 205,
                        "presentTotal": 0,
                        "notVotingTotal": 1,
                    },
                ],
                "legislationType": "HR",
                "legislationNumber": "2811",
            }
        }

        detail = HouseVoteDetail.from_api_response(data)

        assert detail.congress == 118
        assert detail.session == 1
        assert detail.roll_number == 100
        assert detail.question == "Recorded Vote"
        assert detail.result == "Passed"
        assert detail.yea_total == 217
        assert detail.nay_total == 215
        assert detail.present_total == 0
        assert detail.not_voting_total == 3
        assert detail.bill_type == "HR"
        assert detail.bill_number == 2811

    def test_from_api_response_minimal(self) -> None:
        """Test parsing with minimal fields."""
        data = {
            "houseRollCallVote": {
                "congress": 118,
                "sessionNumber": 1,
                "rollCallNumber": 1,
                "votePartyTotal": [],
            }
        }

        detail = HouseVoteDetail.from_api_response(data)

        assert detail.congress == 118
        assert detail.roll_number == 1
        assert detail.yea_total == 0
        assert detail.nay_total == 0


class TestMemberVoteInfo:
    """Tests for MemberVoteInfo dataclass."""

    def test_from_api_response_yea(self) -> None:
        """Test parsing yea vote."""
        data = {
            "bioguideID": "A000001",
            "firstName": "John",
            "lastName": "Smith",
            "voteParty": "R",
            "voteState": "TX",
            "voteCast": "Aye",
        }

        info = MemberVoteInfo.from_api_response(data)

        assert info.bioguide_id == "A000001"
        assert info.name == "Smith, John"
        assert info.party == "R"
        assert info.state == "TX"
        assert info.vote_cast == "Aye"

    def test_from_api_response_nay(self) -> None:
        """Test parsing nay vote."""
        data = {
            "bioguideID": "B000002",
            "firstName": "Jane",
            "lastName": "Jones",
            "voteParty": "D",
            "voteState": "CA",
            "voteCast": "No",
        }

        info = MemberVoteInfo.from_api_response(data)

        assert info.vote_cast == "No"

    def test_from_api_response_not_voting(self) -> None:
        """Test parsing not voting."""
        data = {
            "bioguideID": "C000003",
            "firstName": "Bob",
            "lastName": "Brown",
            "voteCast": "Not Voting",
        }

        info = MemberVoteInfo.from_api_response(data)

        assert info.vote_cast == "Not Voting"
