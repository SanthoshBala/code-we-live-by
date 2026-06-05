# Daily Section Test Status

This file records the results of daily random-section tests comparing the CWLB backend's
parsed representation against the authoritative OLRC source XML.

Each row represents one tested section. "Clean" means no discrepancies were found between
CWLB and the OLRC XML at the stated release point.

| Date       | Title | Section | Heading                                          | Release Point | Status |
|------------|-------|---------|--------------------------------------------------|---------------|--------|
| 2026.05.24 | 17    | 204     | Execution of transfers of copyright ownership    | 113-21        | ✅ Clean |
| 2026.06.05 | 14    | 677     | Turnkey selection procedures                     | 113-21        | ✅ Clean |

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
