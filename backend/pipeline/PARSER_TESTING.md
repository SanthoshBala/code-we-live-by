# Parser Testing Tracker

This file tracks manual validation of the USLM parser output for Task 1.11 (ingestion validation).

## Testing Workflow

```bash
# View a section with all metadata
uv run python -m pipeline.cli normalize-text "17 USC 106" --metadata

# View just provisions (no metadata)
uv run python -m pipeline.cli normalize-text "17 USC 106"
```

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Verified correct |
| ❌ | Has issues (see notes) |
| ⚠️ | Partially correct / needs review |
| ➖ | Not applicable (section has none) |
| ⬜ | Not yet tested |

## Test Sections

| Title | Section | Provisions | Source Laws | References | Amendments | Historical | Editorial | Statutory | Notes |
|-------|---------|------------|-------------|------------|------------|------------|-----------|-----------|-------|
| 10 | § 494 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | Nuclear force reductions |
| 11 | § 763 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | Treatment of accounts |
| 15 | § 6101 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | Telemarketing fraud |
| 17 | § 106 | ✅ | ✅ | ⬜ | ✅ | ✅ | ➖ | ✅ | Exclusive rights (tested during dev) |
| 17 | § 116 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | Negotiated licenses |
| 18 | § 441 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | Postal supply contracts |
| 20 | § 7514 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | Native Hawaiian Education Council |
| 22 | § 3386 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | Taiwan fellows on detail from Government service |
| 26 | § 2043 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | Transfers for insufficient consideration |
| 42 | § 6985 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | Special study on recovery of materials |
| 50 | § 2 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | Consultation and notification requirement |

## Tested Sections Log

### 17 USC 106 - Exclusive rights in copyrighted works
**Tested:** 2026.02.01

**Provisions:** ✅
- 7 lines with correct indentation and markers

**Source Laws:** ✅
- Enactment: PL 94-553 (Copyright Act)
- 5 Amendments correctly identified with dates, paths, and titles

**Amendments:** ✅
- 5 amendments grouped by year (2002, 1999, 1995, 1990×2)
- Changelog-style display working

**Historical Notes:** ✅
- House Report No. 94-1476 content parsed
- 56 lines normalized from prose

**Editorial Notes:** ➖
- Only "Amendments" present (displayed in separate AMENDMENTS section)

**Statutory Notes:** ✅
- Effective Date Of 1995 Amendment
- Effective Date Of 1990 Amendment
- Performing Rights Society Consent Decrees

**Notes:** Used as primary test case during Task 1.11 development.

---

## Known Issues

<!-- Record any parser bugs or edge cases discovered during testing -->

1. *None yet*

## Adding New Test Sections

To add a random section from a title:

```bash
uv run python -c "
import random
from pipeline.olrc.parser import USLMParser
from pathlib import Path

parser = USLMParser()
result = parser.parse_file(Path('data/olrc/title17/usc17.xml'))
sec = random.choice(result.sections)
print(f'§ {sec.section_number} - {sec.heading}')
"
```
