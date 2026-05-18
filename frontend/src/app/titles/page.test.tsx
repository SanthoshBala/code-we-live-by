import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TitlesPage from './page';

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

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

vi.mock('next/navigation', () => ({
  usePathname: () => '/titles',
}));

const titles = [
  {
    title_number: 10,
    title_name: 'Armed Forces',
    is_positive_law: true,
    positive_law_date: '1956-08-10',
    chapter_count: 3,
    section_count: 200,
  },
];

describe('TitlesPage', () => {
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

  it('renders the page heading', async () => {
    render(await TitlesPage(), { wrapper: makeWrapper() });
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Browse the US Code'
    );
  });

  it('renders titles as directory items', async () => {
    render(await TitlesPage(), { wrapper: makeWrapper() });
    expect(screen.getByText(/Armed Forces/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Armed Forces/ })).toHaveAttribute(
      'href',
      '/titles/10'
    );
  });
});
