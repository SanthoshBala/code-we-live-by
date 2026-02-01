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

## Future Sections

*To be documented as decisions are made:*

- Line numbering conventions
- Diff rendering (additions, deletions, modifications)
- Section hierarchy and indentation
- Amendment markers
- Cross-reference linking style
- Blame view attribution format
