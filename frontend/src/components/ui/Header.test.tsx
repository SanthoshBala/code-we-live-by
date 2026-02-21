import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Header from './Header';

// Mock next/link to render a plain anchor
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

vi.mock('@/hooks/useHeadRevision', () => ({
  useHeadRevision: () => ({
    data: {
      revision_id: 1,
      revision_type: 'Release_Point',
      effective_date: '2013-07-18',
      summary: 'Release Point 113-21',
      sequence_number: 1,
    },
    isLoading: false,
    isError: false,
  }),
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe('Header', () => {
  it('renders the logo text linking to home', () => {
    renderWithClient(<Header />);
    const logo = screen.getByText('The Code We Live By');
    expect(logo).toBeInTheDocument();
    expect(logo.closest('a')).toHaveAttribute('href', '/');
  });

  it('renders the Browse Titles nav link', () => {
    renderWithClient(<Header />);
    const link = screen.getByText('Browse Titles');
    expect(link).toBeInTheDocument();
    expect(link.closest('a')).toHaveAttribute('href', '/titles');
  });

  it('displays the head revision info', () => {
    renderWithClient(<Header />);
    expect(screen.getByText(/Release Point 113-21/)).toBeInTheDocument();
    expect(screen.getByText(/Jul 18, 2013/)).toBeInTheDocument();
  });
});
