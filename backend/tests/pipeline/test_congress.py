"""Tests for Congress.gov API client."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.congress.client import (
    BillAction,
    BillAmendment,
    CBOEstimate,
    CongressClient,
    HouseVoteDetail,
    HouseVoteInfo,
    MemberDetail,
    MemberInfo,
    MemberTerm,
    MemberVoteInfo,
    RelatedBill,
    SponsorInfo,
    _parse_cr_refs,
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


class TestParseCRRefs:
    """Tests for Congressional Record reference parsing."""

    def test_no_refs(self) -> None:
        """Text without CR citations returns empty list."""
        assert _parse_cr_refs("Signed by President.") == []

    def test_ref_without_date(self) -> None:
        """Parse CR reference with page only."""
        result = _parse_cr_refs("Considered in House. CR H481.")
        assert result == ["CR H481"]

    def test_ref_with_date(self) -> None:
        """Parse CR reference with date and page range."""
        result = _parse_cr_refs("Debate. CR 2/12/2013 H439-440.")
        assert result == ["CR 2/12/2013 H439-440"]

    def test_senate_page(self) -> None:
        """Parse Senate CR page reference."""
        result = _parse_cr_refs("Senate debate. CR S1234.")
        assert result == ["CR S1234"]

    def test_multiple_refs(self) -> None:
        """Parse multiple CR references from one text string."""
        text = "Debate in House CR H439-440. Senate CR S567."
        result = _parse_cr_refs(text)
        assert len(result) == 2
        assert "CR H439-440" in result
        assert "CR S567" in result

    def test_empty_text(self) -> None:
        """Empty text returns empty list."""
        assert _parse_cr_refs("") == []


class TestBillAction:
    """Tests for BillAction dataclass."""

    def test_from_api_response_presidential_signature(self) -> None:
        """Parse a presidential signature action."""
        data = {
            "actionCode": "36000",
            "actionDate": "2013-08-09",
            "type": "President",
            "text": "Signed by President.",
            "sourceSystem": {"code": 2, "name": "House floor actions"},
        }

        action = BillAction.from_api_response(data)

        assert action.action_date == date(2013, 8, 9)
        assert action.action_code == "36000"
        assert action.action_type == "President"
        assert action.text == "Signed by President."
        assert action.chamber == "House"
        assert action.congressional_record_refs == []

    def test_from_api_response_with_cr_refs(self) -> None:
        """Parse action that includes Congressional Record citations."""
        data = {
            "actionDate": "2013-02-12",
            "type": "Floor",
            "text": "Considered in House. CR 2/12/2013 H439-440.",
            "sourceSystem": {"code": 2, "name": "House floor actions"},
        }

        action = BillAction.from_api_response(data)

        assert action.action_date == date(2013, 2, 12)
        assert action.congressional_record_refs == ["CR 2/12/2013 H439-440"]
        assert action.chamber == "House"

    def test_from_api_response_senate_chamber(self) -> None:
        """Chamber is inferred as Senate from sourceSystem."""
        data = {
            "actionDate": "2013-07-31",
            "type": "Floor",
            "text": "Passed Senate without amendment.",
            "sourceSystem": {"code": 0, "name": "Senate"},
        }

        action = BillAction.from_api_response(data)

        assert action.chamber == "Senate"

    def test_from_api_response_with_recorded_vote(self) -> None:
        """Parse action that includes a recorded vote link."""
        data = {
            "actionDate": "2013-02-13",
            "type": "Floor",
            "text": "On passage Passed by the Yeas and Nays.",
            "sourceSystem": {"code": 2, "name": "House floor actions"},
            "recordedVotes": [
                {
                    "chamber": "House",
                    "congress": 113,
                    "date": "2013-02-13T17:38:00Z",
                    "rollNumber": 47,
                    "session": 1,
                    "url": "http://clerk.house.gov/evs/2013/roll047.xml",
                }
            ],
        }

        action = BillAction.from_api_response(data)

        assert len(action.recorded_votes) == 1
        vote = action.recorded_votes[0]
        assert vote.chamber == "House"
        assert vote.roll_number == 47
        assert vote.session == 1

    def test_from_api_response_missing_date(self) -> None:
        """Action with missing date sets action_date to None."""
        data = {
            "type": "IntroReferral",
            "text": "Referred to committee.",
            "sourceSystem": {},
        }

        action = BillAction.from_api_response(data)

        assert action.action_date is None
        assert action.congressional_record_refs == []

    def test_from_api_response_unknown_source_system(self) -> None:
        """Unknown sourceSystem leaves chamber as None."""
        data = {
            "actionDate": "2013-01-03",
            "type": "IntroReferral",
            "text": "Introduced in House.",
            "sourceSystem": {"code": 9, "name": "Library of Congress"},
        }

        action = BillAction.from_api_response(data)

        assert action.chamber is None


class TestGetBillActions:
    """Tests for CongressClient.get_bill_actions()."""

    @pytest.mark.asyncio
    async def test_fetches_all_pages(self) -> None:
        """get_bill_actions fetches all pages when results exceed page size."""
        page1 = {
            "actions": [
                {
                    "actionDate": "2013-01-03",
                    "type": "IntroReferral",
                    "text": "Introduced in House.",
                    "sourceSystem": {"name": "House floor actions"},
                }
            ],
            "pagination": {"count": 2},
        }
        page2 = {
            "actions": [
                {
                    "actionDate": "2013-08-09",
                    "actionCode": "36000",
                    "type": "President",
                    "text": "Signed by President.",
                    "sourceSystem": {"name": "House floor actions"},
                }
            ],
            "pagination": {"count": 2},
        }

        mock_response1 = MagicMock()
        mock_response1.json.return_value = page1
        mock_response1.raise_for_status = MagicMock()

        mock_response2 = MagicMock()
        mock_response2.json.return_value = page2
        mock_response2.raise_for_status = MagicMock()

        with patch(
            "pipeline.congress.client.CongressClient._request_with_retry",
            new=AsyncMock(side_effect=[mock_response1, mock_response2]),
        ):
            client = CongressClient(api_key="test-key")
            actions = await client.get_bill_actions(113, "hr", 267, page_size=1)

        assert len(actions) == 2
        assert actions[0].action_type == "IntroReferral"
        assert actions[1].action_type == "President"
        assert actions[1].action_code == "36000"

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_actions(self) -> None:
        """get_bill_actions returns empty list when API returns no actions."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"actions": [], "pagination": {"count": 0}}
        mock_response.raise_for_status = MagicMock()

        with patch(
            "pipeline.congress.client.CongressClient._request_with_retry",
            new=AsyncMock(return_value=mock_response),
        ):
            client = CongressClient(api_key="test-key")
            actions = await client.get_bill_actions(113, "hr", 267)

        assert actions == []

    @pytest.mark.asyncio
    async def test_cr_refs_parsed_in_actions(self) -> None:
        """CR references in action text are parsed correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "actions": [
                {
                    "actionDate": "2013-02-12",
                    "type": "Floor",
                    "text": "Debate. CR 2/12/2013 H439-440. CR H481.",
                    "sourceSystem": {"name": "House floor actions"},
                }
            ],
            "pagination": {"count": 1},
        }
        mock_response.raise_for_status = MagicMock()

        with patch(
            "pipeline.congress.client.CongressClient._request_with_retry",
            new=AsyncMock(return_value=mock_response),
        ):
            client = CongressClient(api_key="test-key")
            actions = await client.get_bill_actions(113, "hr", 267)

        assert len(actions) == 1
        assert len(actions[0].congressional_record_refs) == 2


class TestBillAmendment:
    """Tests for BillAmendment dataclass."""

    def test_from_api_response_full(self) -> None:
        """Parse a fully-populated amendment API response."""
        data = {
            "number": "H.AMDT.123",
            "sponsors": [{"fullName": "Rep. Smith, John [D-CA-1]"}],
            "description": "An amendment to strike section 2",
            "purpose": "To reduce spending",
            "proposedDate": "2021-03-15",
            "latestAction": {"actionDate": "2021-03-16", "text": "Amendment agreed to"},
            "status": "adopted",
        }
        amdt = BillAmendment.from_api_response(data)

        assert amdt.amendment_number == "H.AMDT.123"
        assert amdt.sponsor == "Rep. Smith, John [D-CA-1]"
        assert amdt.description == "An amendment to strike section 2"
        assert amdt.purpose == "To reduce spending"
        assert amdt.proposed_date == date(2021, 3, 15)
        assert amdt.action_date == date(2021, 3, 16)
        assert amdt.status == "adopted"

    def test_from_api_response_no_sponsor(self) -> None:
        """Parse amendment with no sponsor."""
        data = {
            "number": "S.AMDT.5",
            "latestAction": {},
        }
        amdt = BillAmendment.from_api_response(data)

        assert amdt.amendment_number == "S.AMDT.5"
        assert amdt.sponsor is None
        assert amdt.proposed_date is None
        assert amdt.action_date is None

    def test_from_api_response_sponsor_fallback(self) -> None:
        """Use name field when fullName is absent."""
        data = {
            "number": "H.AMDT.7",
            "sponsors": [{"name": "Sen. Brown"}],
            "latestAction": {},
        }
        amdt = BillAmendment.from_api_response(data)
        assert amdt.sponsor == "Sen. Brown"


class TestCBOEstimate:
    """Tests for CBOEstimate dataclass."""

    def test_from_api_response_full(self) -> None:
        """Parse a complete CBO estimate."""
        data = {
            "title": "Cost Estimate for H.R. 1234",
            "url": "https://www.cbo.gov/publication/56789",
            "pubDate": "2021-04-01",
            "description": "CBO estimates this bill would cost $1.2 billion over 10 years.",
        }
        est = CBOEstimate.from_api_response(data)

        assert est.title == "Cost Estimate for H.R. 1234"
        assert est.url == "https://www.cbo.gov/publication/56789"
        assert est.pub_date == date(2021, 4, 1)
        assert est.description == "CBO estimates this bill would cost $1.2 billion over 10 years."

    def test_from_api_response_minimal(self) -> None:
        """Parse a minimal CBO estimate with no optional fields."""
        data = {"title": "Informal cost estimate"}
        est = CBOEstimate.from_api_response(data)

        assert est.title == "Informal cost estimate"
        assert est.url is None
        assert est.pub_date is None
        assert est.description is None


class TestRelatedBill:
    """Tests for RelatedBill dataclass."""

    def test_from_api_response_full(self) -> None:
        """Parse a full related bill response."""
        data = {
            "congress": 117,
            "type": "S",
            "number": "500",
            "title": "An identical senate bill",
            "relationshipDetails": [{"type": "Identical bill"}],
        }
        rb = RelatedBill.from_api_response(data)

        assert rb.congress == 117
        assert rb.bill_type == "S"
        assert rb.bill_number == 500
        assert rb.title == "An identical senate bill"
        assert rb.relationship_details == "Identical bill"

    def test_from_api_response_no_relationship(self) -> None:
        """Parse a related bill with no relationship details."""
        data = {
            "congress": 116,
            "type": "HR",
            "number": "42",
            "relationshipDetails": [],
        }
        rb = RelatedBill.from_api_response(data)

        assert rb.bill_type == "HR"
        assert rb.bill_number == 42
        assert rb.relationship_details is None


class TestCongressClientPhase2:
    """Tests for the three new CongressClient methods (Phase 2 history data)."""

    @pytest.mark.asyncio
    async def test_get_bill_amendments_returns_list(self) -> None:
        """get_bill_amendments fetches and parses amendments across pages."""
        page1 = MagicMock()
        page1.json.return_value = {
            "amendments": [
                {
                    "number": "H.AMDT.1",
                    "sponsors": [{"fullName": "Rep. Doe, Jane [D-CA-5]"}],
                    "description": "Strike section 3",
                    "proposedDate": "2021-06-01",
                    "latestAction": {"actionDate": "2021-06-02", "text": "Agreed to"},
                    "status": "adopted",
                }
            ],
            "pagination": {"count": 1},
        }
        page1.raise_for_status = MagicMock()

        with patch(
            "pipeline.congress.client.CongressClient._request_with_retry",
            new=AsyncMock(return_value=page1),
        ):
            client = CongressClient(api_key="test-key")
            amendments = await client.get_bill_amendments(117, "hr", 1234)

        assert len(amendments) == 1
        assert amendments[0].amendment_number == "H.AMDT.1"
        assert amendments[0].sponsor == "Rep. Doe, Jane [D-CA-5]"
        assert amendments[0].action_date == date(2021, 6, 2)
        assert amendments[0].status == "adopted"

    @pytest.mark.asyncio
    async def test_get_bill_amendments_empty_when_404(self) -> None:
        """get_bill_amendments returns empty list on 404."""
        import httpx

        mock_err_response = MagicMock()
        mock_err_response.status_code = 404

        with patch(
            "pipeline.congress.client.CongressClient._request_with_retry",
            new=AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found",
                    request=MagicMock(),
                    response=mock_err_response,
                )
            ),
        ):
            client = CongressClient(api_key="test-key")
            amendments = await client.get_bill_amendments(99, "hr", 9999)

        assert amendments == []

    @pytest.mark.asyncio
    async def test_get_bill_cbo_estimates_returns_list(self) -> None:
        """get_bill_cbo_estimates fetches and parses CBO estimates."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "costEstimates": [
                {
                    "title": "Cost Estimate for H.R. 1234",
                    "url": "https://www.cbo.gov/publication/56789",
                    "pubDate": "2021-04-01",
                    "description": "Costs $1B over 10 years.",
                }
            ],
            "pagination": {"count": 1},
        }
        mock_response.raise_for_status = MagicMock()

        with patch(
            "pipeline.congress.client.CongressClient._request_with_retry",
            new=AsyncMock(return_value=mock_response),
        ):
            client = CongressClient(api_key="test-key")
            estimates = await client.get_bill_cbo_estimates(117, "hr", 1234)

        assert len(estimates) == 1
        assert estimates[0].title == "Cost Estimate for H.R. 1234"
        assert estimates[0].pub_date == date(2021, 4, 1)
        assert estimates[0].url == "https://www.cbo.gov/publication/56789"

    @pytest.mark.asyncio
    async def test_get_bill_cbo_estimates_empty_when_404(self) -> None:
        """get_bill_cbo_estimates returns empty list on 404."""
        import httpx

        mock_err_response = MagicMock()
        mock_err_response.status_code = 404

        with patch(
            "pipeline.congress.client.CongressClient._request_with_retry",
            new=AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found",
                    request=MagicMock(),
                    response=mock_err_response,
                )
            ),
        ):
            client = CongressClient(api_key="test-key")
            estimates = await client.get_bill_cbo_estimates(99, "hr", 9999)

        assert estimates == []

    @pytest.mark.asyncio
    async def test_get_related_bills_returns_list(self) -> None:
        """get_related_bills fetches and parses related bills."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "relatedBills": [
                {
                    "congress": 117,
                    "type": "S",
                    "number": "500",
                    "title": "Senate companion bill",
                    "relationshipDetails": [{"type": "Identical bill"}],
                },
                {
                    "congress": 116,
                    "type": "HR",
                    "number": "42",
                    "title": "Earlier related bill",
                    "relationshipDetails": [{"type": "Related bill"}],
                },
            ],
            "pagination": {"count": 2},
        }
        mock_response.raise_for_status = MagicMock()

        with patch(
            "pipeline.congress.client.CongressClient._request_with_retry",
            new=AsyncMock(return_value=mock_response),
        ):
            client = CongressClient(api_key="test-key")
            related = await client.get_related_bills(117, "hr", 1234)

        assert len(related) == 2
        assert related[0].congress == 117
        assert related[0].bill_type == "S"
        assert related[0].bill_number == 500
        assert related[0].relationship_details == "Identical bill"
        assert related[1].congress == 116

    @pytest.mark.asyncio
    async def test_get_related_bills_empty_when_404(self) -> None:
        """get_related_bills returns empty list on 404."""
        import httpx

        mock_err_response = MagicMock()
        mock_err_response.status_code = 404

        with patch(
            "pipeline.congress.client.CongressClient._request_with_retry",
            new=AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found",
                    request=MagicMock(),
                    response=mock_err_response,
                )
            ),
        ):
            client = CongressClient(api_key="test-key")
            related = await client.get_related_bills(99, "hr", 9999)

        assert related == []
