# Tree Navigator Components

Collapsible tree view for browsing the US Code hierarchy:
Title > Group (chapter, subchapter, subtitle, part, division, ...) > Section > Files.

## Architecture

```
TitleList.tsx        ('use client') root — fetches all titles via useTitles()
  └─ TitleNode.tsx   expandable title row — lazy-loads structure via useTitleStructure()
       └─ GroupNode.tsx    recursive expandable group row (chapter, subchapter, subtitle, part, etc.)
            ├─ GroupNode.tsx   child groups (recursive)
            └─ SectionNode.tsx   expandable section directory
                 ├─ {section_number}    provisions link → /sections/{title}/{section}
                 ├─ EDITORIAL_NOTES     → /sections/{title}/{section}/EDITORIAL_NOTES
                 ├─ STATUTORY_NOTES     → /sections/{title}/{section}/STATUTORY_NOTES
                 └─ HISTORICAL_NOTES    → /sections/{title}/{section}/HISTORICAL_NOTES
icons/
  ├─ FolderIcon.tsx  folder open/closed SVG (used by TreeIndicator)
  └─ FileIcon.tsx    document SVG (used by SectionNode file children)
TreeIndicator.tsx    shared folder icon wrapper (expand/collapse)
```

## Data Flow

1. **TitleList** calls `useTitles()` on mount to fetch all title summaries
2. Each **TitleNode** holds local `expanded` state; when true, `useTitleStructure(n, true)` fires
3. **GroupNode** uses local `useState` for expand/collapse and recursively renders child groups
4. **SectionNode** uses local `useState` for expand/collapse; when expanded, renders file `<Link>` children

## Props

- `compact?: boolean` — passed through the tree for sidebar mode (smaller text/padding)

## Visual Metaphor

The tree uses code-repository visuals to reinforce the "law as code" concept:

- **FolderIcon** (amber) — expandable nodes (titles, groups, sections)
- **FileIcon** (gray) — file children inside sections (provisions + notes)
- **Connector lines** — `border-l` on expanded children containers
- **Path breadcrumbs** — monospace path (e.g. `Title 17 / Chapter 1 / Subchapter A`) above children
- **Section metadata** — right-aligned amendment year and law (e.g. `2020  PL 116-283`)
