# Daily Section Test Status

This file records the results of daily random-section tests comparing the CWLB backend's
parsed representation against the authoritative OLRC source XML.

Each row represents one tested section. "Clean" means no discrepancies were found between
CWLB and the OLRC XML at the stated release point.

| Date       | Title | Section | Heading                                                                                | Release Point | Status |
|------------|-------|---------|----------------------------------------------------------------------------------------|---------------|--------|
| 2026.05.24 | 17    | 204     | Execution of transfers of copyright ownership                                          | 113-21        | ✅ Clean |
| 2026.06.11 | 6     | 231     | Transfer of certain agricultural inspection functions of the Department of Agriculture | 113-21        | ✅ Clean |
| 2026.06.20 | 28    | 2514    | Forfeiture of fraudulent claims                                                        | 113-21        | ✅ Clean (known issue applies — see notes) |

## Notes

### 2026.06.20 — 28 U.S.C. § 2514

All fields matched: heading, body text (2 paragraphs), source credit/citations, Historical and
Revision Notes, Amendments note, Effective Date notes, and all 15 in-note cross-references.

`last_modified_date` is returned as `1992-01-01` instead of the actual amendment date
`1992-10-29` (Pub. L. 102-572 effective date). This is the systemic Jan-1-placeholder bug
already tracked in #466, #483, #491, and #510 — not re-filed here.

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
