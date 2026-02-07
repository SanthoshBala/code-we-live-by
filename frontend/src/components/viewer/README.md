# Viewer Components

Components for rendering a single US Code section in detail.

## Architecture

```
SectionViewer (client, fetches data via useSection hook)
├── SectionHeader        — citation, heading, metadata badges
├── SectionProvisions    — operative law text (whitespace-preserving)
├── AmendmentList        — amendment history grouped by year
├── CitationList         — source law citations with relationship badges
└── SectionNotes         — notes grouped by category (collapsible)
    └── NoteBlock        — single note with indented lines
```

## Data Flow

1. `SectionViewer` calls `useSection(titleNumber, sectionNumber)` which fetches from `/api/v1/sections/{title}/{section}`
2. The response is a `SectionView` object containing `text_content`, `notes`, and metadata
3. Child components receive typed props—no child component fetches data itself

## Key Decisions

- **SectionProvisions** uses `<pre>` with `whitespace-pre-wrap` because the backend returns `text_content` with 4-space indentation already applied
- **SectionNotes** groups notes by `category` (editorial, statutory, historical) and renders each group as a collapsible `<details>` element
- **AmendmentList** sorts amendments newest-first and groups by year
- **CitationList** color-codes relationship badges (Framework, Enactment, Amendment)
