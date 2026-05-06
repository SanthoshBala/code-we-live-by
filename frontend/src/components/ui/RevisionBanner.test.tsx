import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import RevisionBanner from './RevisionBanner';

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
  usePathname: () => '/titles/17',
}));

const mockFetchRevision = vi.fn();
vi.mock('@/lib/api', () => ({
  fetchRevision: (id: number) => mockFetchRevision(id),
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe('RevisionBanner', () => {
  beforeEach(() => {
    mockFetchRevision.mockReset();
  });

  it('renders fallback label while loading', () => {
    mockFetchRevision.mockReturnValue(new Promise(() => {}));
    renderWithClient(<RevisionBanner revision={5} />);

    expect(screen.getByText(/Viewing as of/)).toBeInTheDocument();
    expect(screen.getByText(/Revision 5/)).toBeInTheDocument();
  });

  it('renders revision metadata when loaded', async () => {
    mockFetchRevision.mockResolvedValue({
      revision_id: 5,
      revision_type: 'Release_Point',
      effective_date: '2020-01-15',
      summary: 'Release Point 116-78',
      sequence_number: 5,
    });
    renderWithClient(<RevisionBanner revision={5} />);

    expect(await screen.findByText(/Release Point 116-78/)).toBeInTheDocument();
    expect(screen.getByText(/Jan 15, 2020/)).toBeInTheDocument();
  });

  it('renders "View latest" link pointing to current path without rev param', () => {
    mockFetchRevision.mockReturnValue(new Promise(() => {}));
    renderWithClient(<RevisionBanner revision={5} />);

    const link = screen.getByRole('link', { name: /View latest/i });
    expect(link).toHaveAttribute('href', '/titles/17');
  });

  it('has correct styling classes for amber banner', () => {
    mockFetchRevision.mockReturnValue(new Promise(() => {}));
    const { container } = renderWithClient(<RevisionBanner revision={5} />);

    const banner = container.firstChild as HTMLElement;
    expect(banner).toHaveClass('bg-amber-50');
    expect(banner).toHaveClass('border-amber-300');
  });
});
