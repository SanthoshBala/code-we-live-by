"""Tests for president-by-date lookup utility."""

from datetime import date

from app.core.president_lookup import get_president_by_date, get_president_title


class TestGetPresidentByDate:
    """Tests for get_president_by_date()."""

    def test_obama_signing_date(self) -> None:
        """Pub. L. 113-23 signed 2013-08-09 — Obama was president."""
        assert get_president_by_date(date(2013, 8, 9)) == "Barack Obama"

    def test_obama_start_boundary(self) -> None:
        """First day of Obama's first term."""
        assert get_president_by_date(date(2009, 1, 20)) == "Barack Obama"

    def test_george_w_bush_last_day(self) -> None:
        """Last full day of George W. Bush's presidency is Jan 19 2009."""
        assert get_president_by_date(date(2009, 1, 19)) == "George W. Bush"

    def test_clinton_mid_term(self) -> None:
        """Mid-term Clinton date."""
        assert get_president_by_date(date(1997, 6, 15)) == "Bill Clinton"

    def test_reagan_era(self) -> None:
        """Reagan-era date."""
        assert get_president_by_date(date(1985, 3, 1)) == "Ronald Reagan"

    def test_nixon_resignation_date(self) -> None:
        """Nixon resigned Aug 9 1974; Ford took over same day."""
        assert get_president_by_date(date(1974, 8, 9)) == "Gerald Ford"

    def test_nixon_day_before_resignation(self) -> None:
        """Aug 8 1974 Nixon was still president."""
        assert get_president_by_date(date(1974, 8, 8)) == "Richard Nixon"

    def test_biden_first_day(self) -> None:
        """Biden's inauguration day."""
        assert get_president_by_date(date(2021, 1, 20)) == "Joe Biden"

    def test_trump_second_term_start(self) -> None:
        """Trump's second term start."""
        assert get_president_by_date(date(2025, 1, 20)) == "Donald Trump"

    def test_before_covered_range_returns_unknown(self) -> None:
        """Date before 1961 is outside covered range."""
        assert get_president_by_date(date(1960, 1, 1)) == "Unknown"

    def test_far_future_returns_unknown(self) -> None:
        """Date far past the last covered term returns Unknown."""
        assert get_president_by_date(date(2035, 1, 1)) == "Unknown"


class TestGetPresidentTitle:
    """Tests for get_president_title()."""

    def test_obama(self) -> None:
        assert get_president_title("Barack Obama") == "President Obama"

    def test_george_hw_bush(self) -> None:
        assert get_president_title("George H.W. Bush") == "President Bush"

    def test_johnson(self) -> None:
        assert get_president_title("Lyndon B. Johnson") == "President Johnson"

    def test_unknown(self) -> None:
        assert get_president_title("Unknown") == "Unknown"
