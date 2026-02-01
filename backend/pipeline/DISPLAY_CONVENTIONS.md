# Display Conventions

This document defines how US Code sections are represented as files in the "code as legislation" metaphor.

## Conceptual Mapping

| Legal Concept | Software Analog |
|---------------|-----------------|
| US Code Section | Source file in a repository |
| Provisions | The actual source code |
| Source Laws | Git commits / PRs that created the code |
| Amendments log | CHANGELOG / `git log --oneline` |
| Historical Notes | Design docs / ADRs (rationale from House Reports) |
| Editorial Notes | OLRC annotations (cross-references, clarifications) |
| Statutory Notes | Related config / companion modules (effective dates, etc.) |

## Directory Structure

Each US Code section is represented as a directory containing multiple files:

```
{title}/{section}/
    {section}           # Provisions (the operative law text)
    AMENDMENTS          # Changelog of modifications (like git log)
    HISTORICAL_NOTES    # Historical and Revision Notes
    EDITORIAL_NOTES     # Editorial Notes (OLRC annotations)
    STATUTORY_NOTES     # Statutory Notes and Related Provisions
```

Example for 17 USC 106:

```
17/106/
    106                 # The actual copyright law provisions
    AMENDMENTS          # Chronological list of changes
    HISTORICAL_NOTES    # House Report references, revision notes
    EDITORIAL_NOTES     # Cross-references, amendment summaries
    STATUTORY_NOTES     # Effective dates, related provisions
```

At the Title or Chapter level (TBD based on committee jurisdiction research):

```
{title}/
    OWNERS              # Congressional committees with jurisdiction
    ...
```

### File Naming

- **Provisions file**: Named after the section number (e.g., `106`, `6101`, `494`)
- **Notes files**: SCREAMING_SNAKE_CASE with no extension (like `README`, `LICENSE`)
- **Consistency**: Every section has the same 4 files, even if some are empty

### Why No File Extensions?

Following the Unix convention for special repository files (`README`, `LICENSE`, `CHANGELOG`, `Makefile`), these files use no extension because:
1. They have a consistent, well-defined format
2. They're not meant to be opened by arbitrary editors based on extension
3. The name itself describes the content type

## File Format: Law-Flavored Plain Text

All files use a plain-text format optimized for legal content with preserved indentation structure.

### Format Rules

1. **Headers**: Prefixed with `# ` (level 1) or `## ` (level 2)
2. **Indentation**: 4 spaces per level (no tabs)
3. **Markers**: Legal markers preserved as-is: `(a)`, `(1)`, `(A)`, `(i)`
4. **Blank lines**: Separate logical blocks
5. **Line width**: No hard wrapping (let the renderer wrap)

### Provisions File Example

```
Subject to sections 107 through 122, the owner of copyright under this
title has the exclusive rights to do and to authorize any of the following:
    (1) to reproduce the copyrighted work in copies or phonorecords;
    (2) to prepare derivative works based upon the copyrighted work;
    (3) to distribute copies or phonorecords of the copyrighted work to
        the public by sale or other transfer of ownership, or by rental,
        lease, or lending;
```

### Notes File Example

```
# Historical and Revision Notes

## House Report No. 94-1476
    Section 106 of the bill enumerates the exclusive rights of the copyright
    owner in broad terms...

# Amendments

## 2002
    Pub. L. 107-273 substituted "122" for "121" in introductory provisions.

## 1999
    Pub. L. 106-44 substituted "121" for "120" in introductory provisions.

## 1995
    Pub. L. 104-39 added par. (6).
```

### AMENDMENTS File (Changelog)

The AMENDMENTS file is analogous to a CHANGELOG in software projects. It lists
modifications in reverse chronological order (newest first), grouped by year.

```
# 2002
    PL 107-273  Substituted "122" for "121" in introductory provisions.

# 1999
    PL 106-44   Substituted "121" for "120" in introductory provisions.

# 1995
    PL 104-39   Added par. (6).

# 1990
    PL 101-650  Substituted "120" for "119" in introductory provisions.
    PL 101-318  Substituted "119" for "118" in introductory provisions.

# 1976
    PL 94-553   Original enactment (Copyright Act of 1976).
```

Format:
- `# YYYY` headers group amendments by year
- Each amendment line: `PL {congress}-{number}  {description}`
- Multiple amendments in same year listed under single header
- Original enactment marked as such

### OWNERS File (Committee Jurisdiction)

The OWNERS file lists congressional committees with jurisdiction over the code.
Location TBD based on research (Task 0.15): Title level vs Chapter level.

```
# House
    Judiciary Committee
        Subcommittee on Courts, Intellectual Property, and the Internet

# Senate
    Judiciary Committee
        Subcommittee on Intellectual Property
```

## Mapping to ParsedLine

The format maps directly to the `ParsedLine` data structure:

| Format Element | ParsedLine Field |
|----------------|------------------|
| `# Header` | `is_header=True`, `indent_level=0` |
| `## Subheader` | `is_header=True`, `indent_level=1` |
| `    (a) Text` | `indent_level=1`, `marker="(a)"` |
| `        (1) Text` | `indent_level=2`, `marker="(1)"` |
| `Plain text` | `indent_level=0`, `marker=None` |

### Line Type Detection

```python
def parse_line(line: str) -> ParsedLine:
    if line.startswith("# "):
        return ParsedLine(content=line[2:], is_header=True, indent_level=0)
    if line.startswith("## "):
        return ParsedLine(content=line[3:], is_header=True, indent_level=1)

    # Count leading spaces (4 per level)
    stripped = line.lstrip(" ")
    indent_level = (len(line) - len(stripped)) // 4

    # Extract marker if present
    marker = extract_marker(stripped)  # e.g., "(a)", "(1)"

    return ParsedLine(content=stripped, indent_level=indent_level, marker=marker)
```

## CLI Output

The CLI `normalize-text` command displays sections using this format with additional metadata annotations:

```
PROVISIONS:
----------------------------------------------------------------------
L  1 │ Subject to sections 107 through 122, the owner of copyright...
L  2 │     (1) to reproduce the copyrighted work in copies or phonorecords;
...

HISTORICAL_NOTES:
----------------------------------------------------------------------
# Historical and Revision Notes
    ## House Report No. 94-1476
        Section 106 of the bill enumerates...
```

## Rendering Considerations

### In "File View"
- Provisions displayed as main content
- Notes sections displayed as collapsible documentation below

### In "Blame View"
- Only provisions get blame annotations (source law attribution)
- Notes are metadata about provisions, not part of the operative law

### In "Diff View"
- Show changes to provisions as code diffs
- Show changes to notes as documentation diffs (potentially collapsed by default)
