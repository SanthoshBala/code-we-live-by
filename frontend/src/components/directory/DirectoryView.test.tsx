import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import DirectoryView from './DirectoryView';
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
    id: 'Ch. 1',
    name: 'Subject Matter',
    href: '/titles/17/chapters/1',
    kind: 'folder',
    sectionCount: 12,
  },
];

describe('DirectoryView', () => {
  it('renders the page title (name only)', () => {
    render(
      <DirectoryView
        title="Copyrights"
        breadcrumbs={[{ label: 'Title 17' }]}
        items={items}
      />
    );
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Copyrights'
    );
  });

  it('renders clickable breadcrumbs with current level', () => {
    render(
      <DirectoryView
        title="Copyright Notice, Deposit, and Registration"
        breadcrumbs={[
          { label: 'Title 17', href: '/titles/17' },
          { label: 'Chapter 4' },
        ]}
        items={items}
      />
    );
    const titleLink = screen.getByRole('link', { name: 'Title 17' });
    expect(titleLink).toHaveAttribute('href', '/titles/17');
    expect(screen.getByText('Chapter 4')).toBeInTheDocument();
  });

  it('renders the Code tab as active', () => {
    render(<DirectoryView title="Test" items={items} />);
    expect(screen.getByRole('tab', { name: 'Code' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
  });

  it('renders directory table items', () => {
    render(<DirectoryView title="Test" items={items} />);
    expect(
      screen.getByRole('link', { name: /Subject Matter/ })
    ).toBeInTheDocument();
  });
});
