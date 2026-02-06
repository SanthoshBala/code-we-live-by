# Tree Navigator Components

Collapsible tree view for browsing the US Code hierarchy:
Title > Chapter > Subchapter > Section.

## Architecture

```
TitleList.tsx        ('use client') root — fetches all titles via useTitles()
  ├─ TreeSettingsPanel.tsx  toggle bar for tree lines + breadcrumbs (non-compact only)
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

## Display Settings (TreeDisplayContext)

`TreeDisplayProvider` (wraps the tree in TitleList) exposes two toggles via `useTreeDisplay()`:

- **showTreeLines** — adds `border-l` connector lines on expanded children containers
- **showBreadcrumb** — shows monospace path (e.g. `USC / Title 17 / Ch. 1 / Subch. A`) above expanded children

Settings persist to `localStorage` under the key `cwlb-tree-display`.

## Visual Metaphor

The tree uses code-repository icons to reinforce the "law as code" concept:

- **FolderIcon** (amber) — expandable nodes (titles, chapters, subchapters)
- **FileIcon** (gray) — leaf sections, representing individual code files
- **Section metadata** — right-aligned amendment year and law (e.g. `2020  PL 116-283`)
