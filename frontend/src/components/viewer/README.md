# Viewer Components

Components for rendering US Code section content.

## Architecture

```
Provisions page (/sections/{title}/{section}):
  SectionViewer (client, fetches data via useSection hook)
  ├── SectionHeader        — citation, heading, metadata badges
  └── SectionProvisions    — operative law text (whitespace-preserving)

Notes page (/sections/{title}/{section}/{file}):
  NotesViewer (client, fetches data via useSection hook)
  └── SectionNotes         — notes filtered by category
      └── NoteBlock        — single note with indented lines

Reserved for future blame view:
  ├── AmendmentList        — amendment history grouped by year
  └── CitationList         — source law citations with relationship badges
```

## Data Flow

1. `SectionViewer` calls `useSection(titleNumber, sectionNumber)` which fetches from `/api/v1/sections/{title}/{section}`
2. The response is a `SectionView` object containing `text_content`, `notes`, and metadata
3. `SectionViewer` renders only provisions (header + text content)
4. `NotesViewer` reuses the same hook, filters `notes.notes[]` by category, and passes them to `SectionNotes`

## Key Decisions

- **SectionProvisions** uses `<pre>` with `whitespace-pre-wrap` because the backend returns `text_content` with 4-space indentation already applied
- **SectionNotes** groups notes by `category` (editorial, statutory, historical) and renders each group as a collapsible `<details>` element
- **AmendmentList** and **CitationList** are kept but not rendered on the provisions page — they will power the future blame view
- Notes are split into separate routes (`EDITORIAL_NOTES`, `STATUTORY_NOTES`, `HISTORICAL_NOTES`) to mirror the file-based directory structure in the tree navigator
