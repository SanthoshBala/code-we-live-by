import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TitleList from './TitleList';

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

const titles = [
  {
    title_number: 17,
    title_name: 'Copyrights',
    is_positive_law: true,
    positive_law_date: '1976-10-19',
    chapter_count: 2,
    section_count: 50,
  },
  {
    title_number: 18,
    title_name: 'Crimes and Criminal Procedure',
    is_positive_law: true,
    positive_law_date: '1948-06-25',
    chapter_count: 5,
    section_count: 120,
  },
];

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('TitleList', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(titles), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows loading state initially', () => {
    render(<TitleList />, { wrapper });
    expect(screen.getByText('Loading titles...')).toBeInTheDocument();
  });

  it('renders titles after loading', async () => {
    render(<TitleList />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText(/Copyrights/)).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Crimes and Criminal Procedure/)
    ).toBeInTheDocument();
  });

  it('renders title names as links', async () => {
    render(<TitleList />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText(/Copyrights/)).toBeInTheDocument();
    });
    const link = screen.getByRole('link', { name: /Copyrights/ });
    expect(link).toHaveAttribute('href', '/titles/17');
  });

  it('shows error state on fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('', { status: 500 })
    );
    render(<TitleList />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Failed to load titles.')).toBeInTheDocument();
    });
  });
});
