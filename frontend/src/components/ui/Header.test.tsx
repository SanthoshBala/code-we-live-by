import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
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

describe('Header', () => {
  it('renders the logo text linking to home', () => {
    render(<Header />);
    const logo = screen.getByText('The Code We Live By');
    expect(logo).toBeInTheDocument();
    expect(logo.closest('a')).toHaveAttribute('href', '/');
  });

  it('renders the Browse Titles nav link', () => {
    render(<Header />);
    const link = screen.getByText('Browse Titles');
    expect(link).toBeInTheDocument();
    expect(link.closest('a')).toHaveAttribute('href', '/titles');
  });
});
