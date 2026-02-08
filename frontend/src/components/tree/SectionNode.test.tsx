import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import SectionNode from './SectionNode';

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

const section = {
  section_number: '106',
  heading: 'Exclusive rights in copyrighted works',
  sort_order: 3,
};

describe('SectionNode', () => {
  it('renders the section number and heading', () => {
    render(<SectionNode section={section} titleNumber={17} />);
    expect(screen.getByText(/106/)).toBeInTheDocument();
    expect(
      screen.getByText('Exclusive rights in copyrighted works')
    ).toBeInTheDocument();
  });

  it('renders as a link to the section viewer', () => {
    render(<SectionNode section={section} titleNumber={17} />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/sections/17/106');
  });

  it('applies active styling when isActive', () => {
    render(<SectionNode section={section} titleNumber={17} isActive />);
    const link = screen.getByRole('link');
    expect(link.className).toMatch(/(?<!\S)bg-primary-50(?!\S)/);
  });

  it('does not apply active styling by default', () => {
    render(<SectionNode section={section} titleNumber={17} />);
    const link = screen.getByRole('link');
    expect(link.className).not.toMatch(/(?<!\S)bg-primary-50(?!\S)/);
  });
});
