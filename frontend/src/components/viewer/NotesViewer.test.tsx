import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import NotesViewer from './NotesViewer';
import type { SectionView } from '@/lib/types';

const sectionData: SectionView = {
  title_number: 17,
  section_number: '106',
  heading: 'Exclusive rights in copyrighted works',
  full_citation: '17 U.S.C. § 106',
  text_content: 'The owner of copyright...',
  enacted_date: '1976-10-19',
  last_modified_date: '2020-01-01',
  is_positive_law: true,
  is_repealed: false,
  notes: {
    citations: [],
    amendments: [],
    short_titles: [],
    notes: [
      {
        header: 'References in Text',
        content: 'The Act referred to in subsection (a)...',
        lines: [],
        category: 'editorial',
      },
      {
        header: 'Short Title',
        content: '',
        lines: [
          {
            line_number: 1,
            content: 'This Act may be cited as the "Copyright Act of 1976".',
            indent_level: 0,
            marker: null,
            is_header: false,
          },
        ],
        category: 'statutory',
      },
      {
        header: 'Amendments',
        content: '',
        lines: [
          {
            line_number: 1,
            content: '2002—Subsec. (a). Pub. L. 107–273 amended heading.',
            indent_level: 0,
            marker: null,
            is_header: false,
          },
        ],
        category: 'historical',
      },
    ],
    has_notes: true,
    has_citations: false,
    has_amendments: false,
    transferred_to: null,
    omitted: false,
    renumbered_from: null,
  },
};

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('NotesViewer', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(sectionData), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows loading state initially', () => {
    render(
      <NotesViewer
        titleNumber={17}
        sectionNumber="106"
        file="EDITORIAL_NOTES"
      />,
      { wrapper }
    );
    expect(screen.getByText('Loading notes...')).toBeInTheDocument();
  });

  it('renders only editorial notes for EDITORIAL_NOTES file', async () => {
    render(
      <NotesViewer
        titleNumber={17}
        sectionNumber="106"
        file="EDITORIAL_NOTES"
      />,
      { wrapper }
    );
    await waitFor(() => {
      expect(screen.getByText('References in Text')).toBeInTheDocument();
    });
    expect(screen.queryByText('Short Title')).not.toBeInTheDocument();
    expect(screen.queryByText('Amendments')).not.toBeInTheDocument();
  });

  it('renders only statutory notes for STATUTORY_NOTES file', async () => {
    render(
      <NotesViewer
        titleNumber={17}
        sectionNumber="106"
        file="STATUTORY_NOTES"
      />,
      { wrapper }
    );
    await waitFor(() => {
      expect(screen.getByText('Short Title')).toBeInTheDocument();
    });
    expect(screen.queryByText('References in Text')).not.toBeInTheDocument();
  });

  it('renders only historical notes for HISTORICAL_NOTES file', async () => {
    render(
      <NotesViewer
        titleNumber={17}
        sectionNumber="106"
        file="HISTORICAL_NOTES"
      />,
      { wrapper }
    );
    await waitFor(() => {
      expect(screen.getByText('Amendments')).toBeInTheDocument();
    });
    expect(screen.queryByText('References in Text')).not.toBeInTheDocument();
  });

  it('shows empty state when no notes match category', async () => {
    const noNotes = {
      ...sectionData,
      notes: { ...sectionData.notes!, notes: [] },
    };
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(noNotes), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
    render(
      <NotesViewer
        titleNumber={17}
        sectionNumber="106"
        file="EDITORIAL_NOTES"
      />,
      { wrapper }
    );
    await waitFor(() => {
      expect(
        screen.getByText('No editorial notes for this section.')
      ).toBeInTheDocument();
    });
  });

  it('shows error state on fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('', { status: 500 })
    );
    render(
      <NotesViewer
        titleNumber={17}
        sectionNumber="106"
        file="EDITORIAL_NOTES"
      />,
      { wrapper }
    );
    await waitFor(() => {
      expect(screen.getByText('Failed to load section.')).toBeInTheDocument();
    });
  });
});
