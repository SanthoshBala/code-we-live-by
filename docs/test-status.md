# Daily Section Test Status

This file records the results of daily random-section tests comparing the CWLB backend's
parsed representation against the authoritative OLRC source XML.

Each row represents one tested section. "Clean" means no discrepancies were found between
CWLB and the OLRC XML at the stated release point.

| Date       | Title | Section | Heading                                                                                | Release Point | Status |
|------------|-------|---------|----------------------------------------------------------------------------------------|---------------|--------|
| 2026.05.20 | 21    | 692     | Inspection extended to reindeer                                                        | 113-21        | ✅ Clean |
| 2026.05.24 | 17    | 204     | Execution of transfers of copyright ownership                                          | 113-21        | ✅ Clean |
| 2026.05.28 | 29    | 567     | Labor-management dispute settlement expenses                                          | 113-21        | ✅ Clean |
| 2026.06.05 | 14    | 677     | Turnkey selection procedures                                                           | 113-21        | ✅ Clean |
| 2026.06.10 | 49    | 11707   | Liability when property is delivered in violation of routing instructions             | 113-21        | ✅ Clean |
| 2026.06.11 | 6     | 231     | Transfer of certain agricultural inspection functions of the Department of Agriculture | 113-21        | ✅ Clean |
| 2026.06.12 | 29    | 521     | Investigations by Secretary; applicability of other laws                              | 113-21        | ✅ Clean |
| 2026.06.15 | 25    | 349     | Patents in fee to allottees                                                            | 113-21        | ✅ Clean |
| 2026.06.20 | 28    | 2514    | Forfeiture of fraudulent claims                                                        | 113-21        | ✅ Clean (known issue applies — see notes) |
| 2026.06.22 | 5     | 569     | Encouraging negotiated rulemaking                                                      | 113-21        | ✅ Clean |
| 2026.06.24 | 33    | 2284b   | Scenic and aesthetic considerations                                                    | 113-21        | ✅ Clean |
| 2026.06.26 | 3     | 456     | Confidentiality                                                                        | 113-21        | ✅ Clean |
| 2026.06.29 | 44    | 910     | Congressional Record: subscriptions; sale of current, individual numbers, and bound sets; postage rate | 113-21 | ✅ Clean (known issue applies — see notes) |
| 2026.07.08 | 9     | 8       | Proceedings begun by libel in admiralty and seizure of vessel or property              | 113-21        | ✅ Clean |
| 2026.07.26 | 33    | 401     | Construction of bridges, causeways, dams or dikes generally; exemptions                | 113-21        | ✅ Clean |
| 2026.07.27 | 28    | 1391    | Venue generally                                                                        | 113-21        | ✅ Clean |
| 2026.07.28 | 17    | 106     | Exclusive rights in copyrighted works                                                  | 113-21        | ⚠️ Known issues apply (see notes) |
| 2026.07.29 | 37    | 206     | Reserves; members of National Guard: inactive-duty training                            | 113-21        | ✅ Clean (known issue applies — see notes) |
| 2026.07.30 | 31    | 5311    | Declaration of purpose                                                                 | 113-21        | ✅ Clean (known issue applies — see notes) |
| 2026.07.31 | 9     | 10      | Same; vacation; grounds; rehearing                                                     | 113-21        | ✅ Clean (known issue applies — see notes) |
| 2026.08.02 | 43    | 597a    | Easements for Bull Lake Dam and Reservoir                                              | 113-21        | ✅ Clean |
| 2026.08.03 | 17    | 107     | Limitations on exclusive rights: Fair use                                              | 113-21        | ✅ Clean (known issues confirmed — see notes) |

## Notes

### 2026.06.20 — 28 U.S.C. § 2514

All fields matched: heading, body text (2 paragraphs), source credit/citations, Historical and
Revision Notes, Amendments note, Effective Date notes, and all 15 in-note cross-references.

`last_modified_date` is returned as `1992-01-01` instead of the actual amendment date
`1992-10-29` (Pub. L. 102-572 effective date). This is the systemic Jan-1-placeholder bug
already tracked in #466, #483, #491, and #510 — not re-filed here.

### 2026.06.29 — 44 U.S.C. § 910

Heading and full body text (subsections (a)–(c)) match verbatim, including "Public Printer"
terminology — correct for this release point, since the 2014 rename to "Director of the
Government Publishing Office" (Pub. L. 113–235) postdates 113-21. Enactment and amendment
citations, and the Historical and Revision Notes / Amendments notes, all match the OLRC XML
exactly.

`last_modified_date` is returned as `1974-01-01` instead of the actual amendment date
`1974-06-08` (visible in the same response's `notes.citations[1].law.date`). This is the same
systemic Jan-1-placeholder bug already tracked in #466, #483, #491, #510, #538, and #546 (most
recently #548), and already has a correct, reviewed fix sitting unmerged in PR #469 — not
re-filed here.

### 2026.07.27 — 28 U.S.C. § 1391

All fields matched: heading, full body text (subsections (a)–(g)), source credit, all
13 citations in the source credit, 19 amendment history entries, and all 8 note sections
(Historical and Revision Notes, References in Text, Amendments, and 5 Effective Date notes
for the 2011, 2002, 1992, 1988, and 1976 amendments). `last_modified_date` is correctly
set to `2011-12-07` (actual PL 112-63 enactment date) — no Jan-1 placeholder bug on this
section. Data staleness (only one revision ingested, release point 113-21 from 2013) is a
systemic known issue tracked in #483, #564, #578, #583 — not re-filed here. Since the
section was last amended in December 2011, the text at release point 113-21 matches the
current OLRC prelim verbatim.


### 2026.07.28 — 17 U.S.C. § 106

Section heading, main text (6 numbered paragraphs), source credit, enacted date
(`1976-10-19`), and `last_modified_date` (`2002-11-02`) all match the OLRC XML.
Amendment notes (5 entries) and effective-date notes (2 entries) are all present and
correct. Four of five citation path_displays are now correct (§3(d), §704(b)(2), §1(g)(2),
§2 — consistent with a partial fix since issue #525 was filed in June).

Two known-issue occurrences found and commented on existing open issues:

1. **Citation path drops terminal uppercase-letter subparagraph** (issue #525) — The
   citation for Pub. L. 107–273 shows `path_display: "§13210(4)"` but the OLRC
   `href` is `/us/pl/107/273/dC/tIII/s13210/4/A` and the raw text reads
   `§ 13210(4)(A)`. The `(A)` suffix is still being dropped. Comment added to #525.

2. **Heading-only `historicalAndRevision` note silently dropped** (issue #217) — The OLRC
   XML contains a `<note topic="historicalAndRevision">` with only a
   `<heading>Historical and Revision Notes</heading>` child and no body elements. This
   note does not appear in CWLB's `notes.notes` array. The four substantive notes that
   follow it (house report, amendments, two effective-date notes) are all present and
   correctly separated — an improvement over the full-collapse behaviour described in #217
   — but the heading-only container node is still dropped. Comment added to #217.


### 2026.07.29 — 37 U.S.C. § 206

Compared CWLB against the current OLRC prelim (PL 119-100, 2026-06-26). Differences found:

- **Heading**: CWLB returns "Reserves; members of National Guard: inactive-duty training";
  current OLRC heading is "Reserves; members of National Guard; members of the Space Force:
  inactive-duty training" ("members of the Space Force" added by 2025 amendment).
- **Text body**: CWLB text omits Space Force coverage in subsection (a) (2025 amendment) and
  the parental/family leave provision in subsection (a) (2021/2023 amendments).
- **`last_modified_date`**: CWLB returns `2008-01-28`, consistent with Pub. L. 110-181
  (enacted 2008-01-28, the most recent amendment within release point 113-21). Not a parsing
  error.

All discrepancies are attributable to the known stale-ingestion defect: CWLB is at release
point 113-21 (2013-01-01) while the current OLRC is at PL 119-100 (2026-06-26), a gap of
~13 years. No novel parsing errors were found. Comment added to #578; stale-data defect class
already tracked in #578, #583, #564, #485.


### 2026.07.30 — 31 U.S.C. § 5311

CWLB returns the pre-2021 single-sentence text for "Declaration of purpose" (`last_modified_date:
"2001-10-26"`, `is_repealed: false`). The current OLRC text is the five-provision enumerated
version enacted by the Anti-Money Laundering Act of 2020 (Pub. L. 116–283, div. F, title LXI,
§6101(a), Jan. 1, 2021, 134 Stat. 4549), which completely repealed and replaced the prior
single-sentence provision. The extensive notes added by Pub. L. 116–283 (severability,
interagency coordination, personnel rotation, information-sharing frameworks, innovation
officer positions, supervisory teams, regulatory reviews) are also absent. All discrepancies
are attributable to the known stale release point already tracked in #583.


### 2026.07.31 — 9 U.S.C. § 10

All fields matched: heading ("Same; vacation; grounds; rehearing"), full body text (subsections
(a) chapeau + paragraphs (1)–(4), (b), (c)), source credit, enacted date (1947-07-30), and
last_modified_date (2002-05-07). Derivation note (category: historical) and Amendments note
(category: editorial) both match the OLRC XML verbatim, including all six amendment paragraphs
for 2002, 1992, and 1990 changes. In-note cross-references to Pub. L. 107-169, 102-354, and
101-552 are all present and correct. The `is_positive_law: true` and `group_ancestors` (Chapter 1)
fields are accurate.

`notes.amendments[*].law` objects for all four citation entries have `date: null`,
`official_title: null`, `short_title: null`, `stat_volume: null`, `stat_page: null`,
`stat_reference: null`, and `display_title: null` — only `congress`, `law_number`, and
`public_law_id` are populated. This is the systemic amendment law metadata null bug already
tracked in #561 — not re-filed; commented on that issue with this occurrence.

OLRC XML used: release point 119-102 (current as of 2026-07-12), downloaded from
`https://uscode.house.gov/download/releasepoints/us/pl/119/102/xml_usc09@119-102.zip`.
Section was last amended in 2002 so content is identical between 113-21 and 119-102.


### 2026.08.02 — 43 U.S.C. § 597a

Simple unamended section (enacted Mar. 14, 1940; never amended). All fields matched: heading,
full body text (single unnumbered paragraph), source credit, enacted date, no notes, no
amendments, and group ancestors (Chapter 12 / Subchapter XVII). The apparent text difference
between CWLB and the OLRC HTML view (spaces before commas in "Provided ," and "title 25 ,")
is an HTML rendering artifact from OLRC hyperlink markup — the underlying statutory text is
identical. No new bugs filed.


### 2026.08.03 — 17 U.S.C. § 107 (Fair use)

Statutory text matches OLRC verbatim: all four fair-use factors plus the 1992 unpublished-works
sentence. Source credit matches exactly (PL 94-553, PL 101-650, PL 102-492). Historical and
Revision Notes (H.Rpt. 94-1476, ~12,000 words), classroom copying agreement, books/periodicals
guidelines, and music education guidelines are all present with full content. Two amendment
entries are present (1992 and 1990). Structure, heading, enacted date (1976-10-19), and
last_modified_date (1992-10-24) are all correct.

Two known defects confirmed active on this section:
- **Issue #652**: `Effective Date of 1990 Amendment` note returned with `category: "statutory"`
  instead of `"editorial"`. § 107 is already listed in that issue's evidence table.
- **Issue #561**: `notes.amendments[*].law` objects have `date`, `official_title`,
  `short_title`, `stat_volume`, `stat_page`, and `stat_reference` all `null` for both
  PL 102-492 and PL 101-650. Already filed specifically about this section.

No new defects found. Comments added to both issues confirming reproduction.

## Test methodology

1. `GET /api/v1/revisions/latest?title={title}` — determine current release point.
2. `GET /api/v1/titles` — pick a title at random.
3. `GET /api/v1/titles/{title}/structure` — pick a non-repealed section at random.
4. `GET /api/v1/sections/{title}/{section}` — fetch CWLB's parsed representation.
5. Download OLRC XML bulk zip for the matching release point:
   `https://uscode.house.gov/download/releasepoints/us/pl/{congress}/{law}/xml_usc{title}@{release}.zip`
6. Parse the XML and compare: heading, main text provisions, source credit, enacted date,
   amendment history, and notes (historical, editorial, statutory).
7. File a GitHub issue with label `bug` for each discrepancy found; otherwise update this file.

## Fields checked

- Section heading
- All subsection/paragraph text (chapeau, content, indentation)
- Source credit / enacted date / last modified date
- Citations and amendments in notes
- Historical and revision notes (full text)
- Editorial notes
- Cross-references
- `is_repealed`, `is_positive_law`, `group_ancestors`
