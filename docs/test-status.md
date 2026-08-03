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
