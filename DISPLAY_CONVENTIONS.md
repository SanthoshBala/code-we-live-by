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
# Source Laws
PL 94-553      1976.10.19    enacted
PL 101-318     1990.07.03    amended § 3(d)
PL 101-650     1990.12.01    amended § 704(b)(2)
```

**Rationale:**

1. **Changelog familiarity**: The columnar format mirrors version control logs (`git log --oneline`) and changelogs, making provenance immediately scannable.

2. **Non-programmer accessibility**: Unlike `import` or `use` statements, this format reads as plain metadata without requiring programming knowledge.

3. **Date format**: Uses `YYYY.MM.DD` for chronological sorting and international clarity, consistent with project conventions.

4. **Concise identifiers**: `PL 94-553` is the normalized Public Law identifier, balancing brevity with recognizability.

**Alternatives considered:**

| Style | Example | Reason not chosen |
|-------|---------|-------------------|
| `from PL import` | `from PL 94-553 import § 101` | Too code-like for metadata |
| Prose format | `Enacted by Pub. L. 94-553...` | Verbose; harder to scan |
| Legal citation | `Pub. L. 94–553, title I, § 101` | Unfamiliar to non-lawyers |

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

## Future Sections

*To be documented as decisions are made:*

- Line numbering conventions
- Diff rendering (additions, deletions, modifications)
- Section hierarchy and indentation
- Blame view attribution format
