import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import DirectoryTable from './DirectoryTable';
import type { DirectoryItem } from '@/lib/types';

vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const items: DirectoryItem[] = [
  {
    id: 'Title 17',
    name: 'Copyrights',
    href: '/titles/17',
    kind: 'folder',
    sectionCount: 50,
    lastAmendmentLaw: 'PL 116-283',
    lastAmendmentYear: 2021,
  },
  {
    id: 'Title 10',
    name: 'Armed Forces',
    href: '/titles/10',
    kind: 'folder',
    sectionCount: 120,
    lastAmendmentLaw: 'PL 117-81',
    lastAmendmentYear: 2022,
  },
];

const fileItems: DirectoryItem[] = [
  {
    id: '\u00A7\u2009106',
    name: 'Exclusive rights',
    href: '/sections/17/106',
    kind: 'file',
    lastAmendmentLaw: 'PL 110-403',
    lastAmendmentYear: 2008,
  },
];

describe('DirectoryTable', () => {
  it('renders column headers including ID and # Sections', () => {
    render(<DirectoryTable items={items} />);
    expect(screen.getByText(/^ID/)).toBeInTheDocument();
    expect(screen.getByText(/^Name/)).toBeInTheDocument();
    expect(screen.getByText(/# Sections/)).toBeInTheDocument();
    expect(screen.getByText(/Last amended by/)).toBeInTheDocument();
    expect(screen.getByText(/^Date/)).toBeInTheDocument();
  });

  it('hides # Sections column when no items have section counts', () => {
    render(<DirectoryTable items={fileItems} />);
    expect(screen.queryByText(/# Sections/)).not.toBeInTheDocument();
  });

  it('renders item IDs and names separately', () => {
    render(<DirectoryTable items={items} />);
    expect(screen.getByText('Title 17')).toBeInTheDocument();
    expect(screen.getByText('Copyrights')).toBeInTheDocument();
    expect(screen.getByText('Armed Forces')).toBeInTheDocument();
  });

  it('renders section counts in dedicated column', () => {
    render(<DirectoryTable items={items} />);
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('120')).toBeInTheDocument();
  });

  it('renders items as links', () => {
    render(<DirectoryTable items={items} />);
    const links = screen.getAllByRole('link');
    expect(links[0]).toHaveAttribute('href', '/titles/10');
  });

  it('renders amendment metadata in columns', () => {
    render(<DirectoryTable items={items} />);
    expect(screen.getByText('PL 116-283')).toBeInTheDocument();
    expect(screen.getByText('2021')).toBeInTheDocument();
  });

  it('renders empty state when no items', () => {
    render(<DirectoryTable items={[]} />);
    expect(screen.getByText('No items found.')).toBeInTheDocument();
  });

  it('defaults to ID ascending sort with sort indicator', () => {
    render(<DirectoryTable items={items} />);
    const indicator = screen.getByLabelText('sorted ascending');
    expect(indicator).toBeInTheDocument();
    // First row should be Title 10 (sorts before Title 17 numerically)
    const links = screen.getAllByRole('link');
    expect(links[0]).toHaveTextContent('Title 10');
  });

  it('toggles sort direction on clicking the same column', async () => {
    const user = userEvent.setup();
    render(<DirectoryTable items={items} />);

    // Click ID header again to switch to descending
    await user.click(screen.getByText(/^ID/));
    expect(screen.getByLabelText('sorted descending')).toBeInTheDocument();
    // First row should now be Title 17
    const links = screen.getAllByRole('link');
    expect(links[0]).toHaveTextContent('Title 17');
  });

  it('sorts by a different column when clicking it', async () => {
    const user = userEvent.setup();
    render(<DirectoryTable items={items} />);

    // Click Date header
    await user.click(screen.getByText(/^Date/));
    expect(screen.getByLabelText('sorted ascending')).toBeInTheDocument();
    // 2021 should come before 2022
    const links = screen.getAllByRole('link');
    expect(links[0]).toHaveTextContent('Title 17');
  });
});
