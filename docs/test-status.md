# CWLB Parsing Test Status

This file records manual spot-checks of CWLB's parsed representation against the authoritative OLRC source.

## Test Log

### 2026.05.20 — 21 U.S.C. § 692 (CLEAN)

| Field | Value |
|---|---|
| **Title** | 21 — Food and Drugs |
| **Section** | 692 — "Inspection extended to reindeer" |
| **OLRC release point** | 113-21 |
| **CWLB revision** | 1 (effective 2013-01-01) |
| **Source XML** | `usc21@113-21.xml` from OLRC bulk download |

**Fields verified:**

- Heading ✓ — matches OLRC (`"Inspection extended to reindeer"`)
- Main text ✓ — exact match ("The provisions of the meat-inspection law may be extended to the inspection of reindeer.")
- Source credit / citation ✓ — June 30, 1914, ch. 131, 38 Stat. 420
- Codification note 1 ✓ — "Section was enacted as part of the appropriation act cited as the credit to this section and not as part of the Federal Meat Inspection Act which is classified to subchapters I to IV–A of this chapter."
- Codification note 2 ✓ — "Section was formerly classified to section 94 of this title."
- Amendment history ✓ — no amendments in OLRC source; CWLB correctly shows empty amendments list
- Cross-reference ✓ — `/us/usc/t21/s94` correctly extracted from codification note

**Result:** No discrepancies found. CWLB representation is complete and accurate for this section.
