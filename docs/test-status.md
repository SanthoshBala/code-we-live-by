# Daily OLRC Spot-Check Status

Records of the daily routine that compares a randomly selected US Code section ingested by CWLB against the authoritative OLRC source at the same release point.

## 2026.06.29 — 44 U.S.C. § 910

- **Title:** 44 (Public Printing and Documents)
- **Section:** 910 ("Congressional Record: subscriptions; sale of current, individual numbers, and bound sets; postage rate")
- **Release point:** OLRC 113-21 (effective 2013-01-01), per `GET /api/v1/revisions/latest?title=44`
- **OLRC source:** `https://uscode.house.gov/download/releasepoints/us/pl/113/21/xml_usc44@113-21.zip` → `usc44@113-21.xml`

### Result: clean

Compared CWLB's `GET /api/v1/sections/44/910` response against the OLRC USLM XML for release point 113-21:

- Heading and full body text (subsections (a)–(c)) match verbatim, including "Public Printer" terminology — correct for this release point, since the 2014 rename to "Director of the Government Publishing Office" (Pub. L. 113–235) postdates 113-21.
- Enactment + amendment citations match the `sourceCredit` exactly: Pub. L. 90–620 (Oct. 22, 1968, 82 Stat. 1260) and Pub. L. 93–314, § 1(a) (June 8, 1974, 88 Stat. 239).
- "Historical and Revision Notes" and "Amendments" notes match the OLRC XML's `<notes>` block exactly, including the reference to 44 U.S. Code 1964 ed. § 188 and the 1974 amendment description.
- `enacted_date` (1968-10-22) matches the enactment citation exactly.

### Known issue observed (not re-filed)

`last_modified_date` is returned as `1974-01-01` instead of the actual amendment date `1974-06-08` (visible in the same response's `notes.citations[1].law.date`). This is the same systemic "year-only / Jan-1 placeholder" bug already filed in issues #466, #483, #491, #510, #538, and #546 (most recently #548), and already has a correct, reviewed fix sitting unmerged in PR #469 since 2026-05-27. No new issue was filed to avoid further duplication.

## 2026.06.26 — 3 U.S.C. § 456

See PR #545.

## 2026.06.24 — 33 U.S.C. § 2284b

See PR #541.

## 2026.06.22 — 5 U.S.C. § 569

See PR #535.

## 2026.06.20 — 28 U.S.C. § 2514

See PR #532.
