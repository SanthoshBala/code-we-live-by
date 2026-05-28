# Morning Validation Test Log

Each entry records a spot-check of one US Code section: CWLB's parsed representation
vs. the authoritative OLRC XML source at the same release point.

---

## 2026.05.28

**Title:** 29 (Labor)
**Section:** §567 — Labor-management dispute settlement expenses
**Release point:** 113-21 (effective 2013-01-01)
**CWLB revision ID:** 1

### What was checked

| Field | Result |
|---|---|
| Section heading | ✓ Match |
| Main text (one paragraph) | ✓ Exact match |
| Source credit (Pub. L. 102–394, title I, § 101, Oct. 6, 1992, 106 Stat. 1798) | ✓ Match |
| Prior Provisions note — entry count | ✓ 9 of 9 present |
| Prior Provisions note — text content (all 9 lines) | ✓ Exact character-for-character match including en dashes and narrow no-break spaces (U+202F) |
| Amendment count | ✓ 0 (correct) |
| Repealed flag | ✓ False (correct) |

### Methodology

1. `GET /api/v1/revisions/latest?title=29` → revision 1, release point 113-21.
2. `GET /api/v1/titles/29/structure` → 539 sections enumerated; §567 selected via
   `random.seed(20260528)`.
3. `GET /api/v1/sections/29/567` → CWLB parsed representation.
4. OLRC prelim viewer (`uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title29-section567`)
   used for visual reference; authoritative comparison performed against the OLRC bulk XML
   download (`xml_usc29@113-21.zip`) to verify character-level fidelity.
5. All note lines compared with `repr()` to catch invisible Unicode differences.

### Result: **CLEAN — no bugs filed**
