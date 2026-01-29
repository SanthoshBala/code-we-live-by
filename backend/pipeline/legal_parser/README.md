# Legal Language Parser

This module extracts structured amendment information from Public Law text, translating legislative drafting conventions into actionable diffs that can be applied to the US Code.

## The Challenge: From Bill Text to Code Changes

When Congress passes a law that modifies existing statute, the bill text doesn't contain a diff—it contains **instructions written in legal prose**. For example:

```
Section 106(3) of title 17, United States Code, is amended by
striking "or by rental, lease, or lending" and inserting
"by rental, lease, or lending, or by transmission".
```

This single sentence must be parsed to extract:
- **Target**: Title 17, Section 106, Subsection (3)
- **Operation**: Strike and insert (i.e., replace)
- **Old text**: "or by rental, lease, or lending"
- **New text**: "by rental, lease, or lending, or by transmission"

Only then can we generate an actual diff showing what changed.

## Amendment Pattern Categories

### 1. Strike and Insert (Most Common)

The bread-and-butter of legislative amendments. Replaces specific quoted text.

```
Section X is amended by striking "old text" and inserting "new text".
```

**Variations observed across eras:**

| Era | Phrasing |
|-----|----------|
| Pre-2000 | `striking out "X" and inserting in lieu thereof "Y"` |
| Modern | `striking "X" and inserting "Y"` |
| Multi-location | `striking "X" each place such term appears and inserting "Y"` |

### 2. Strike Only (Deletion)

Removes text without replacement.

```
Section X is amended by striking "text to remove".
```

**Complex variants:**
- `striking "X" and all that follows through the period` — Deletes from quoted text to end of sentence
- `striking paragraph (3)` — Removes entire structural unit
- `striking the second sentence` — Positional reference

### 3. Add/Insert (Addition)

Adds new text at a specified location.

```
Section X is amended by adding at the end the following:
"(4) new paragraph text here."
```

**Location specifiers:**
- `adding at the end` — Append to section/subsection
- `inserting after paragraph (2)` — Insert between existing paragraphs
- `inserting before "specific text"` — Insert at precise location
- `inserting after section 106 the following new section` — Add entire new section

### 4. Substitute (Complete Replacement)

Replaces an entire section or subsection with new text.

```
Section 106 is amended to read as follows:
"§ 106. [Entire new section text...]"
```

This pattern requires extracting all text following "as follows:" until the next section marker.

### 5. Repeal

Removes an entire section from the Code.

```
Section 115 is hereby repealed.
```

**Variants:**
- `Section X is repealed` (without "hereby")
- `paragraph (3) is stricken`
- `by striking section X` (within a larger amendment)

### 6. Redesignate (Renumbering)

Changes section/paragraph numbers without modifying content.

```
by redesignating paragraphs (3) and (4) as paragraphs (4) and (5)
```

This is often paired with insertions (make room for new paragraph by renumbering existing ones).

### 7. Transfer

Moves a section from one location to another.

```
Section 105 is transferred to chapter 2 of title 17.
```

## Stylistic Evolution Over Time

Legislative drafting conventions have evolved:

| Period | Characteristics |
|--------|-----------------|
| **Pre-1990s** | "striking out", "in lieu thereof", "be amended as follows" |
| **1990s-2000s** | Transition period with mixed styles |
| **2010s-Present** | Standardized "striking" and "inserting", cleaner structure |

The parser handles both old and new conventions to support historical law analysis.

## Section Reference Complexity

Section references can be simple or deeply nested:

| Reference | Meaning |
|-----------|---------|
| `Section 106` | Top-level section |
| `Section 106(a)` | Subsection (a) |
| `Section 106(a)(1)` | Paragraph (1) of subsection (a) |
| `Section 106(a)(1)(A)` | Subparagraph (A) |
| `Section 106(a)(1)(A)(i)` | Clause (i) — 4 levels deep |

References may also include:
- Title: `Section 106 of title 17`
- Full citation: `Section 106 of title 17, United States Code`
- Popular name: `Section 102 of the Copyright Act`

## From Pattern Match to Diff

The translation process:

```
┌─────────────────────────────────────────────────────────────┐
│  Public Law Text                                            │
│  "Section 106(3) is amended by striking 'X' and            │
│   inserting 'Y'"                                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Pattern Matching (this module)                             │
│  - Identify pattern type: STRIKE_INSERT                     │
│  - Extract section ref: title=17, section=106, subsec=(3)   │
│  - Extract old_text: "X"                                    │
│  - Extract new_text: "Y"                                    │
│  - Assign confidence score                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Section Lookup (future: Task 1.11)                         │
│  - Fetch current text of 17 USC § 106(3) from database     │
│  - Locate "X" within the section text                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Diff Generation (future: Task 1.11)                        │
│  - old_text → new_text replacement                          │
│  - Generate unified diff                                    │
│  - Store in LawChange table                                 │
└─────────────────────────────────────────────────────────────┘
```

## Confidence Scoring

Not all pattern matches are equally reliable. The parser assigns confidence scores:

| Confidence | Meaning |
|------------|---------|
| **0.95-1.0** | High confidence, direct text extraction |
| **0.85-0.94** | Good confidence, may need verification |
| **< 0.85** | Lower confidence, flag for manual review |

Factors affecting confidence:
- Pattern specificity (quoted text > general amendment)
- Section reference completeness (with title > without)
- Text extraction success (both old/new found > partial)

## Patterns Requiring Manual Review

Some patterns cannot be fully automated:

1. **"Add at the end the following"** — New text must be extracted from subsequent lines
2. **"To read as follows"** — Entire replacement text follows
3. **Ambiguous section references** — "such section" without clear antecedent
4. **Cross-references** — "as amended by section 3 of this Act"

These are flagged with `needs_review=True` for human verification.

## Usage

```python
from pipeline.legal_parser import AmendmentParser

# Create parser with default title context
parser = AmendmentParser(default_title=17)

# Parse amendment text
text = 'Section 106 is amended by striking "X" and inserting "Y".'
amendments = parser.parse(text)

for amendment in amendments:
    print(f"Pattern: {amendment.pattern_type}")
    print(f"Section: {amendment.section_ref}")
    print(f"Old text: {amendment.old_text}")
    print(f"New text: {amendment.new_text}")
    print(f"Confidence: {amendment.confidence}")
    print(f"Needs review: {amendment.needs_review}")
```

## Pattern Coverage

Currently supported (26 patterns):

- Strike and insert (5 variants)
- Strike only (4 variants)
- Add/insert (6 variants)
- Repeal (3 variants)
- Redesignate (2 variants)
- Substitute (2 variants)
- Transfer (1 variant)
- General amendment (3 variants)

## References

- [House Practice: Amendments](https://www.govinfo.gov/content/pkg/GPO-HPRACTICE-112/html/GPO-HPRACTICE-112-3.htm) — Official House drafting guidelines
- [Deschler's Precedents: Motions to Strike](https://govinfo.gov/content/pkg/GPO-HPREC-DESCHLERS-V9/html/GPO-HPREC-DESCHLERS-V9-1-4-3.htm)
- [OLRC USLM Schema](https://uscode.house.gov/download/resources/USLM-User-Guide.pdf) — XML markup for US Code

## Future Enhancements

- USLM XML parsing for structured amendments (113th Congress+)
- Machine learning for ambiguous pattern resolution
- Cross-reference resolution ("as defined in section X")
- Confidence calibration based on manual review feedback
