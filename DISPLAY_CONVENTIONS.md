# Display Conventions

This document defines the aesthetic and formatting conventions for how CWLB renders the US Code. The goal is to present legal text using idioms familiar from software development while remaining accessible to non-programmers.

---

## Comments and Annotations

### Section-Level Comments (Statutory Notes)

Statutory notes—such as effective dates, transfer of functions, and cross-references—are rendered as **comment blocks** using the `#` prefix on each line.

**Syntax:**
```
# NOTE: Effective Date
# This section takes effect on the date that is
# 180 days after the date of enactment.
# See Pub. L. 117-263, §5101(b).
```

**Rationale:**

1. **Clear line-by-line demarcation**: Every line is unambiguously marked as annotation, avoiding "am I still in the comment?" confusion.

2. **Familiar but not intimidating**: The `#` symbol is widely recognized from configuration files, spreadsheets, and lightweight scripting languages (Python, Shell, YAML, Ruby). It doesn't carry the "heavy programming" connotations of C-style `/* */` blocks.

3. **Semantic resonance**: In everyday usage, `#` connotes "note" or "number"—appropriate for marginalia.

4. **Precedent**: This is the canonical comment style in Python, the backend language of this project, and is standard practice for multi-line comments in languages without block comment syntax.

**Alternatives considered:**

| Style | Example | Reason not chosen |
|-------|---------|-------------------|
| `>` blockquote | `> NOTE: ...` | Implies quotation rather than annotation |
| `\|` pipe | `\| NOTE: ...` | Less established as comment marker |
| `/* */` block | `/* NOTE: ... */` | More visually complex; reads as "code" |
| `"""` triple-quote | `""" NOTE: """` | Python-specific; technically a string literal |
| `--` double-dash | `-- NOTE: ...` | Could be confused with em-dash in prose |

---

## Source Laws

Source laws identify the Public Laws that enacted or amended a section. These appear as metadata at the top of a section, similar to a changelog or git blame view.

**Syntax:**
```
SOURCE LAWS:
----------------------------------------------------------------------
# 1976.10.19    Enactment  PL 94-553    tit. I, §101
# 1990.07.03    Amendment  PL 101-318   §3(d)
# 2002.11.02    Amendment  PL 107-273   div. C, tit. III, §13210(4)(A)
```

**Column order:** `{date} {Enactment/Amendment} {law} {path}`

**Path format:** Uses standard Bluebook abbreviations for hierarchical levels:
- `div.` — Division (e.g., `div. C`)
- `tit.` — Title (e.g., `tit. III`)
- `§` — Section, no space after symbol (e.g., `§101`, `§13210(4)(A)`)

**Rationale:**

1. **Changelog familiarity**: The columnar format mirrors version control logs (`git log --oneline`) and changelogs, making provenance immediately scannable. Date-first ordering emphasizes chronology.

2. **Comment prefix**: Each line uses the `#` comment style, visually distinguishing metadata from code.

3. **Hierarchical path**: Public Laws can have complex structures (divisions, titles, subtitles, chapters, parts, sections). The path captures the full location within the law using standard legal abbreviations from the Bluebook.

4. **Date format**: Uses `YYYY.MM.DD` for chronological sorting and international clarity, consistent with project conventions.

5. **Enactment vs Amendment**: Clear terminology—"Enactment" for the original law, "Amendment" for subsequent modifications.

**Supported path levels** (from OLRC conventions):

| Level | Abbreviation | Example |
|-------|--------------|---------|
| Division | `div.` | `div. C` |
| Title | `tit.` | `tit. III` |
| Subtitle | `subtit.` | `subtit. A` |
| Chapter | `ch.` | `ch. 1` |
| Subchapter | `subch.` | `subch. II` |
| Part | `pt.` | `pt. A` |
| Subpart | `subpt.` | `subpt. 1` |
| Section | `§` | `§101` |

**Alternatives considered:**

| Style | Example | Reason not chosen |
|-------|---------|-------------------|
| `from PL import` | `from PL 94-553 import § 101` | Too code-like for metadata |
| Prose format | `Enacted by Pub. L. 94-553...` | Verbose; harder to scan |
| Full legal citation | `Pub. L. 94–553, title I, § 101` | More verbose; unfamiliar to non-lawyers |
| `enacted`/`amended` | lowercase action | Ambiguous—could mean the law was amended |
| No abbreviations | `division C, title III` | Too verbose for columnar display |

---

## In-Line References

In-line references are cross-references within statutory text to other sections of the US Code. These use a structured syntax inspired by programming language import statements.

**Syntax:**
```
from title 17 use § 106
from title 26 use § 501(a)
from this title use §§ 107-122
use subsection (a)(1)
```

**Rationale:**

1. **`use` keyword**: Draws from Rust (`use crate::module`), PHP (`use Namespace\Class`), and Pascal/Delphi. Implies "this code depends on" without the "importing code" connotation.

2. **`from ... use ...` order**: Places the source (title) first, then the specific provision. This reads naturally: "from the tax code, use section 501."

3. **Omitting `from` for local references**: When referencing within the same title, `use subsection (a)(1)` suffices—similar to relative imports in Python.

**Language inspirations:**

| Language | Syntax | What we borrowed |
|----------|--------|------------------|
| **Rust** | `use crate::module::item;` | The `use` keyword |
| **Python** | `from module import symbol` | The `from X ... Y` pattern |
| **PHP** | `use Namespace\Class;` | `use` for dependencies |
| **Haskell** | `import Module (symbol)` | Parenthetical specificity |
| **Go** | `import "pkg/path"` | Path-like hierarchy |

**Examples in context:**

Original statutory text:
> "Subject to sections 107 through 122, the owner of copyright..."

Rendered with structured reference:
> "Subject to `from this title use §§ 107-122`, the owner of copyright..."

Or in a hover/tooltip:
> "Subject to sections 107 through 122 [`→ 17 U.S.C. §§ 107-122`], the owner..."

---

## Tree Navigator Labels

### Folder rows show names only; identifiers move to breadcrumbs

In the sidebar tree, each expandable node (title, chapter, subchapter) displays **only its name** — not the hierarchy prefix or identifier. The legal identifier appears in the **breadcrumb path** shown when the node is expanded.

**Before:**
```
📁 Title 17 — Copyrights
   📁 Chapter 1 — Subject Matter
      📁 Subchapter A — The Works
      breadcrumb: USC / Title 17 / Ch. 1 / Subch. A
```

**After:**
```
📁 Copyrights
   📁 Subject Matter
      📁 The Works
      breadcrumb: Title 17 / Ch. 1 / Subch. A
```

**Rationale:**

1. **Scannability**: In a narrow sidebar, "Armed Forces" is instantly recognizable. "Title 10 — Armed Forces" wastes half the row on a number most users don't know by heart.

2. **Legal legibility preserved**: The title/chapter/subchapter numbers are the primary way lawyers and researchers cite these sections. Rather than removing them entirely, they appear in the breadcrumb path that is visible whenever a node is expanded — one click away, always in context.

3. **Redundancy reduction**: The hierarchy type (Title, Chapter, Subchapter) is already communicated by the tree depth and the folder icon. Repeating it in the label is redundant.

4. **Breadcrumb prefix**: The `USC /` prefix was dropped from breadcrumbs because the entire application is scoped to the US Code — the context is implicit.

---

## Future Sections

*To be documented as decisions are made:*

- Line numbering conventions
- Diff rendering (additions, deletions, modifications)
- Section hierarchy and indentation
- Blame view attribution format
