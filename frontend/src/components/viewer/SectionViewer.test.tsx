import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import SectionViewer from './SectionViewer';
import type { SectionView } from '@/lib/types';

vi.mock('@/hooks/useSection', () => ({
  useSection: vi.fn(),
}));

import { useSection } from '@/hooks/useSection';

const mockUseSection = vi.mocked(useSection);

const baseSectionData: SectionView = {
  title_number: 17,
  section_number: '106',
  heading: 'Exclusive rights in copyrighted works',
  full_citation: '17 U.S.C. § 106',
  text_content: '(a) In General',
  provisions: null,
  enacted_date: '1976-10-19',
  last_modified_date: '2020-01-01',
  is_positive_law: true,
  is_repealed: false,
  notes: {
    citations: [
      {
        law: {
          congress: 94,
          law_number: 553,
          date: '1976-10-19',
          public_law_id: 'PL 94-553',
        },
        law_id: 'PL 94-553',
        law_title: 'Copyright Act of 1976',
        relationship: 'Enactment',
        raw_text: 'Pub. L. 94-553, title I, § 106',
      },
    ],
    amendments: [
      {
        law: {
          congress: 116,
          law_number: 283,
          public_law_id: 'PL 116-283',
          date: '2021-01-01',
        },
        year: 2021,
        description: 'Amended subsection (a)',
        public_law_id: 'PL 116-283',
      },
      {
        law: {
          congress: 110,
          law_number: 403,
          public_law_id: 'PL 110-403',
          date: '2008-10-13',
        },
        year: 2008,
        description: 'Amended subsection (b)',
        public_law_id: 'PL 110-403',
      },
    ],
    short_titles: [],
    notes: [],
    has_notes: false,
    has_citations: true,
    has_amendments: true,
    transferred_to: null,
    omitted: false,
    renumbered_from: null,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('SectionViewer', () => {
  it('renders loading state', () => {
    mockUseSection.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useSection>);

    render(<SectionViewer titleNumber={17} sectionNumber="106" />);
    expect(screen.getByText('Loading section...')).toBeInTheDocument();
  });

  it('renders error state', () => {
    mockUseSection.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
    } as ReturnType<typeof useSection>);

    render(<SectionViewer titleNumber={17} sectionNumber="106" />);
    expect(screen.getByText('Failed to load section.')).toBeInTheDocument();
  });

  it('extracts and displays the latest amendment in the header', () => {
    mockUseSection.mockReturnValue({
      data: baseSectionData,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useSection>);

    render(<SectionViewer titleNumber={17} sectionNumber="106" />);
    expect(screen.getByText('PL 116-283')).toBeInTheDocument();
    expect(screen.getByText(/2021/)).toBeInTheDocument();
  });

  it('shows tabs when amendments or citations exist', () => {
    mockUseSection.mockReturnValue({
      data: baseSectionData,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useSection>);

    render(<SectionViewer titleNumber={17} sectionNumber="106" />);
    expect(screen.getByRole('tab', { name: 'Code' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'History' })).toBeInTheDocument();
  });

  it('does not show tabs when no amendments or citations', () => {
    const dataWithoutHistory: SectionView = {
      ...baseSectionData,
      notes: {
        ...baseSectionData.notes!,
        amendments: [],
        citations: [],
        has_amendments: false,
        has_citations: false,
      },
    };
    mockUseSection.mockReturnValue({
      data: dataWithoutHistory,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useSection>);

    render(<SectionViewer titleNumber={17} sectionNumber="106" />);
    expect(screen.queryByRole('tab')).toBeNull();
  });

  it('defaults to Code tab showing provisions', () => {
    mockUseSection.mockReturnValue({
      data: baseSectionData,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useSection>);

    render(<SectionViewer titleNumber={17} sectionNumber="106" />);

    expect(screen.getByRole('tab', { name: 'Code' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
    expect(screen.getByRole('tab', { name: 'History' })).toHaveAttribute(
      'aria-selected',
      'false'
    );
    // Provisions visible, history not
    expect(
      screen.getByRole('heading', {
        name: 'Exclusive rights in copyrighted works',
      })
    ).toBeInTheDocument();
    expect(screen.queryByText('Amendment History')).toBeNull();
  });

  it('switches between Code and History tabs', async () => {
    mockUseSection.mockReturnValue({
      data: baseSectionData,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useSection>);

    render(<SectionViewer titleNumber={17} sectionNumber="106" />);

    // Click History tab
    await userEvent.click(screen.getByRole('tab', { name: 'History' }));
    expect(screen.getByText('Amendment History')).toBeInTheDocument();
    expect(screen.getByText('Source Laws')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'History' })).toHaveAttribute(
      'aria-selected',
      'true'
    );

    // Click Code tab to go back
    await userEvent.click(screen.getByRole('tab', { name: 'Code' }));
    expect(screen.queryByText('Amendment History')).toBeNull();
    expect(screen.getByRole('tab', { name: 'Code' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
  });
});
