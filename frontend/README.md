# CWLB Frontend

Next.js 14 frontend for The Code We Live By.

## Architecture

```
src/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx          # Root layout (QueryProvider + Header)
│   ├── page.tsx            # Home page with navigation cards
│   └── globals.css         # Tailwind base styles
├── components/
│   ├── QueryProvider.tsx   # TanStack React Query client provider
│   └── ui/                 # Shared UI components
│       ├── Header.tsx      # App header with logo and navigation
│       ├── Sidebar.tsx     # Collapsible left panel for tree navigation
│       └── MainLayout.tsx  # Sidebar + main content flex layout
├── lib/                    # Shared utilities and API client (future)
└── test/
    └── setup.ts            # Vitest + Testing Library setup
```

## Data Flow

1. **QueryProvider** wraps the app with TanStack React Query for server state management
2. **Header** provides top-level navigation (Browse Titles link)
3. **MainLayout** composes an optional **Sidebar** with a main content area
4. Pages fetch data via React Query hooks (to be added in Tasks 1A.6-1A.8)

## Key Decisions

- **Server components by default**: Only `QueryProvider` is a client component (`'use client'`)
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
