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
