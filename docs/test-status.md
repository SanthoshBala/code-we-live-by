# Test Status

This file records the results of the daily automated spot-check that compares
CWLB's ingested representation of a randomly selected US Code section against
the authoritative OLRC source (XML bulk download) for the same release point.

Entries are appended in reverse chronological order. Only "clean" results
(no discrepancies found) are recorded here — discrepancies are filed as GitHub
issues with the `bug` label instead.

## 2026.06.12

- **Section**: 29 U.S.C. § 521 (Investigations by Secretary; applicability of other laws)
- **Release point**: 113-21 (effective 2013-01-01)
- **Result**: Clean. Heading, provision text, source credit/citation
  (Pub. L. 86-257, 73 Stat. 539), and "References in Text" editorial note all
  match the OLRC XML (`xml_usc29@113-21.zip`) exactly. The split of subsection
  (a) into two provision lines (one per sentence, with the second indented at
  level 1) matches the project's documented sentence-splitting convention in
  `backend/pipeline/DISPLAY_CONVENTIONS.md`.
