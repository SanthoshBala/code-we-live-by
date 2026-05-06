"""Static lookup for US presidents by date of service.

Used to annotate presidential signature events with the president's name
when the PublicLaw.president field is not populated.
"""

from __future__ import annotations

from datetime import date

# (start_date, end_date, full_name) — ordered chronologically.
# Start date is the inauguration/succession date (inclusive).
# End date is the last day in office — i.e. one day before the successor's
# start (so inauguration day belongs to the incoming president, not the
# outgoing one). For mid-term successions the successor's start equals the
# departure date (e.g. Ford started the same day Nixon resigned).
_PRESIDENTS: list[tuple[date, date, str]] = [
    (date(1961, 1, 20), date(1963, 11, 21), "John F. Kennedy"),
    (date(1963, 11, 22), date(1969, 1, 19), "Lyndon B. Johnson"),
    (date(1969, 1, 20), date(1974, 8, 8), "Richard Nixon"),
    (date(1974, 8, 9), date(1977, 1, 19), "Gerald Ford"),
    (date(1977, 1, 20), date(1981, 1, 19), "Jimmy Carter"),
    (date(1981, 1, 20), date(1989, 1, 19), "Ronald Reagan"),
    (date(1989, 1, 20), date(1993, 1, 19), "George H.W. Bush"),
    (date(1993, 1, 20), date(2001, 1, 19), "Bill Clinton"),
    (date(2001, 1, 20), date(2009, 1, 19), "George W. Bush"),
    (date(2009, 1, 20), date(2017, 1, 19), "Barack Obama"),
    (date(2017, 1, 20), date(2021, 1, 19), "Donald Trump"),
    (date(2021, 1, 20), date(2025, 1, 19), "Joe Biden"),
    (date(2025, 1, 20), date(2029, 1, 19), "Donald Trump"),
]


def get_president_by_date(enacted_date: date) -> str:
    """Return the full name of the US president serving on a given date.

    Args:
        enacted_date: The date to look up (e.g. a law's enactment date).

    Returns:
        Full name string (e.g. "Barack Obama"), or "Unknown" if the date
        falls outside the covered range.
    """
    for start, end, name in _PRESIDENTS:
        if start <= enacted_date <= end:
            return name
    return "Unknown"


def get_president_title(full_name: str) -> str:
    """Return the display title for a president (e.g. "President Obama").

    Uses the last word of the full name as the surname. Handles hyphenated
    last names (e.g. "George H.W. Bush" → "President Bush").

    Args:
        full_name: Full name as returned by get_president_by_date().

    Returns:
        Display string like "President Obama" or "Unknown" if full_name
        is "Unknown".
    """
    if full_name == "Unknown":
        return "Unknown"
    surname = full_name.rsplit(" ", 1)[-1]
    return f"President {surname}"
