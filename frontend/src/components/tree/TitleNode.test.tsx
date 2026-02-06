import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TitleNode from './TitleNode';

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

const title = {
  title_number: 17,
  title_name: 'Copyrights',
  is_positive_law: true,
  positive_law_date: '1976-10-19',
  chapter_count: 2,
  section_count: 50,
};

const structure = {
  title_number: 17,
  title_name: 'Copyrights',
  is_positive_law: true,
  chapters: [
    {
      chapter_number: '1',
      chapter_name: 'Subject Matter',
      sort_order: 1,
      subchapters: [],
      sections: [
        { section_number: '101', heading: 'Definitions', sort_order: 1 },
      ],
    },
  ],
};

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('TitleNode', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(structure), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the title name and section count', () => {
    render(<TitleNode title={title} />, { wrapper });
    expect(screen.getByText(/Copyrights/)).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
  });

  it('does not fetch structure until expanded', () => {
    render(<TitleNode title={title} />, { wrapper });
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('fetches and renders structure on expand', async () => {
    const user = userEvent.setup();
    render(<TitleNode title={title} />, { wrapper });
    await user.click(screen.getByText(/Copyrights/));
    await waitFor(() => {
      expect(screen.getByText(/Subject Matter/)).toBeInTheDocument();
    });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/titles/17/structure'
    );
  });
});
