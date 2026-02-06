# CWLB Frontend

Next.js 14 frontend for The Code We Live By.

## Architecture

```
src/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx          # Root layout (QueryProvider + Header)
│   ├── page.tsx            # Home page with navigation cards
│   ├── titles/page.tsx     # Browse Titles — full-page tree navigator
│   ├── sections/[titleNumber]/[sectionNumber]/
│   │   └── page.tsx        # Section viewer (placeholder for Task 1A.7)
│   └── globals.css         # Tailwind base styles
├── components/
│   ├── QueryProvider.tsx   # TanStack React Query client provider
│   ├── tree/               # Collapsible US Code tree navigator
│   │   ├── TitleList.tsx   # ('use client') root — fetches titles
│   │   ├── TitleNode.tsx   # Expandable title row (lazy-loads structure)
│   │   ├── ChapterNode.tsx # Expandable chapter row
│   │   ├── SubchapterNode.tsx # Expandable subchapter row
│   │   ├── SectionLeaf.tsx # Leaf link to section viewer
│   │   └── TreeIndicator.tsx # Expand/collapse chevron
│   └── ui/                 # Shared UI components
│       ├── Header.tsx      # App header with logo and navigation
│       ├── Sidebar.tsx     # Collapsible left panel for tree navigation
│       └── MainLayout.tsx  # Sidebar + main content flex layout
├── hooks/
│   ├── useTitles.ts        # React Query hook for title list
│   └── useTitleStructure.ts # React Query hook for title structure (lazy)
├── lib/
│   ├── types.ts            # TypeScript interfaces for API responses
│   └── api.ts              # Fetch helpers for backend API
└── test/
    └── setup.ts            # Vitest + Testing Library setup
```

## Data Flow

1. **QueryProvider** wraps the app with TanStack React Query for server state management
2. **Header** provides top-level navigation (Browse Titles link)
3. **TitleList** fetches all title summaries on mount via `useTitles()`
4. Expanding a **TitleNode** triggers `useTitleStructure()` to lazy-load chapters/sections
5. **SectionLeaf** links to `/sections/{titleNumber}/{sectionNumber}`
6. The section page uses **MainLayout** with a compact **TitleList** in the **Sidebar**

## Key Decisions

- **Server components by default**: Only `QueryProvider` and `TitleList` are client components
- **Lazy loading**: Title structure is only fetched when a title is expanded
- **TanStack React Query**: 5-minute stale time, single retry for API calls
- **Tailwind CSS**: Uses custom `primary` color palette defined in `tailwind.config.ts`
- **API proxy**: `next.config.js` rewrites `/api/*` to `localhost:8000` during development

## Commands

```bash
npm run dev           # Start dev server (port 3000)
npm run build         # Production build
npm run lint          # ESLint
npm run format        # Prettier (write)
npm run format:check  # Prettier (check only)
npm run type-check    # TypeScript type checking
npm run test          # Vitest (watch mode)
npm run test -- --run # Vitest (single run)
```
