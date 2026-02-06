import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import SectionLeaf from './SectionLeaf';

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

describe('SectionLeaf', () => {
  it('renders the section number and heading', () => {
    render(<SectionLeaf section={section} titleNumber={17} />);
    expect(screen.getByText('§ 106')).toBeInTheDocument();
    expect(
      screen.getByText('Exclusive rights in copyrighted works')
    ).toBeInTheDocument();
  });

  it('links to the correct section URL', () => {
    render(<SectionLeaf section={section} titleNumber={17} />);
    const link = screen
      .getByText('Exclusive rights in copyrighted works')
      .closest('a');
    expect(link).toHaveAttribute('href', '/sections/17/106');
  });

  it('applies compact styling when compact is true', () => {
    const { container } = render(
      <SectionLeaf section={section} titleNumber={17} compact />
    );
    const link = container.querySelector('a');
    expect(link?.className).toContain('text-xs');
  });
});
