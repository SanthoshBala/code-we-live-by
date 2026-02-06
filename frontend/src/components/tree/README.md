# Tree Navigator Components

Collapsible tree view for browsing the US Code hierarchy:
Title > Chapter > Subchapter > Section.

## Architecture

```
TitleList.tsx        ('use client') root — fetches all titles via useTitles()
  └─ TitleNode.tsx   expandable title row — lazy-loads structure via useTitleStructure()
       └─ ChapterNode.tsx    expandable chapter row
            ├─ SubchapterNode.tsx   expandable subchapter row (receives chapterNumber prop)
            │    └─ SectionLeaf.tsx   leaf link to /sections/{title}/{section}
            └─ SectionLeaf.tsx       direct chapter sections
icons/
  ├─ FolderIcon.tsx  folder open/closed SVG (used by TreeIndicator)
  └─ FileIcon.tsx    document SVG (used by SectionLeaf)
TreeIndicator.tsx    shared folder icon wrapper (expand/collapse)
```

## Data Flow

1. **TitleList** calls `useTitles()` on mount to fetch all title summaries
2. Each **TitleNode** holds local `expanded` state; when true, `useTitleStructure(n, true)` fires
3. **ChapterNode** and **SubchapterNode** use local `useState` for expand/collapse
4. **SectionLeaf** renders a Next.js `<Link>` to the section viewer page

## Props

- `compact?: boolean` — passed through the tree for sidebar mode (smaller text/padding)

## Visual Metaphor

The tree uses code-repository visuals to reinforce the "law as code" concept:

- **FolderIcon** (amber) — expandable nodes (titles, chapters, subchapters)
- **FileIcon** (gray) — leaf sections, representing individual code files
- **Connector lines** — `border-l` on expanded children containers
- **Path breadcrumbs** — monospace path (e.g. `USC / Title 17 / Ch. 1 / Subch. A`) above children
- **Section metadata** — right-aligned amendment year and law (e.g. `2020  PL 116-283`)
