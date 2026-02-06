# Tree Navigator Components

Collapsible tree view for browsing the US Code hierarchy:
Title > Chapter > Subchapter > Section.

## Architecture

```
TitleList.tsx        ('use client') root — fetches all titles via useTitles()
  └─ TitleNode.tsx   expandable title row — lazy-loads structure via useTitleStructure()
       └─ ChapterNode.tsx    expandable chapter row
            ├─ SubchapterNode.tsx   expandable subchapter row
            │    └─ SectionLeaf.tsx   leaf link to /sections/{title}/{section}
            └─ SectionLeaf.tsx       direct chapter sections
TreeIndicator.tsx    shared chevron icon (expand/collapse)
```

## Data Flow

1. **TitleList** calls `useTitles()` on mount to fetch all title summaries
2. Each **TitleNode** holds local `expanded` state; when true, `useTitleStructure(n, true)` fires
3. **ChapterNode** and **SubchapterNode** use local `useState` for expand/collapse
4. **SectionLeaf** renders a Next.js `<Link>` to the section viewer page

## Props

- `compact?: boolean` — passed through the tree for sidebar mode (smaller text/padding)
