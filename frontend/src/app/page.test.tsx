import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Home from './page';

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

describe('Home', () => {
  it('renders the main heading', () => {
    render(<Home />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'The Code We Live By'
    );
  });

  it('renders navigation cards', () => {
    render(<Home />);
    expect(screen.getByText('Browse Titles')).toBeInTheDocument();
    expect(screen.getByText('Search')).toBeInTheDocument();
    expect(screen.getByText('Recent Laws')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
  });

  it('links Browse Titles to /titles', () => {
    render(<Home />);
    const link = screen.getByText('Browse Titles').closest('a');
    expect(link).toHaveAttribute('href', '/titles');
  });

  it('marks placeholder cards as coming soon', () => {
    render(<Home />);
    const badges = screen.getAllByText('Coming soon');
    expect(badges).toHaveLength(3);
  });
});
