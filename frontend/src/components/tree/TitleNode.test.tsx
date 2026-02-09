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
  children: [
    {
      group_type: 'chapter',
      number: '1',
      name: 'Subject Matter',
      sort_order: 1,
      children: [],
      sections: [
        { section_number: '101', heading: 'Definitions', sort_order: 1 },
      ],
    },
  ],
  sections: [],
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

  it('renders the title name as a link', () => {
    render(<TitleNode title={title} />, { wrapper });
    const link = screen.getByRole('link', { name: /Copyrights/ });
    expect(link).toHaveAttribute('href', '/titles/17');
  });

  it('does not fetch structure until expanded', () => {
    render(<TitleNode title={title} />, { wrapper });
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('icon click expands and fetches structure', async () => {
    const user = userEvent.setup();
    render(<TitleNode title={title} />, { wrapper });
    await user.click(screen.getByRole('button', { name: 'Expand' }));
    await waitFor(() => {
      expect(screen.getByText(/Subject Matter/)).toBeInTheDocument();
    });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/titles/17/structure'
    );
  });

  it('icon click collapses expanded tree', async () => {
    const user = userEvent.setup();
    render(<TitleNode title={title} />, { wrapper });
    await user.click(screen.getByRole('button', { name: 'Expand' }));
    await waitFor(() => {
      expect(screen.getByText(/Subject Matter/)).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: 'Collapse' }));
    expect(screen.queryByText(/Subject Matter/)).not.toBeInTheDocument();
  });
});
