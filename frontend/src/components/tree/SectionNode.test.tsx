import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

const sectionWithAmendment = {
  ...section,
  last_amendment_year: 2020,
  last_amendment_law: 'PL 116-283',
};

describe('SectionNode', () => {
  it('renders the section number and heading', () => {
    render(<SectionNode section={section} titleNumber={17} />);
    expect(screen.getByText('§ 106')).toBeInTheDocument();
    expect(
      screen.getByText('Exclusive rights in copyrighted works')
    ).toBeInTheDocument();
  });

  it('does not show file children when collapsed', () => {
    render(<SectionNode section={section} titleNumber={17} />);
    expect(screen.queryByText('EDITORIAL_NOTES')).not.toBeInTheDocument();
  });

  it('shows 4 file children when expanded', async () => {
    const user = userEvent.setup();
    render(<SectionNode section={section} titleNumber={17} />);

    await user.click(screen.getByRole('button'));

    expect(screen.getByText('106')).toBeInTheDocument();
    expect(screen.getByText('EDITORIAL_NOTES')).toBeInTheDocument();
    expect(screen.getByText('STATUTORY_NOTES')).toBeInTheDocument();
    expect(screen.getByText('HISTORICAL_NOTES')).toBeInTheDocument();
  });

  it('generates correct URLs for file children', async () => {
    const user = userEvent.setup();
    render(<SectionNode section={section} titleNumber={17} />);

    await user.click(screen.getByRole('button'));

    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(4);
    expect(links[0]).toHaveAttribute('href', '/sections/17/106');
    expect(links[1]).toHaveAttribute(
      'href',
      '/sections/17/106/EDITORIAL_NOTES'
    );
    expect(links[2]).toHaveAttribute(
      'href',
      '/sections/17/106/STATUTORY_NOTES'
    );
    expect(links[3]).toHaveAttribute(
      'href',
      '/sections/17/106/HISTORICAL_NOTES'
    );
  });

  it('collapses children on second click', async () => {
    const user = userEvent.setup();
    render(<SectionNode section={section} titleNumber={17} />);

    await user.click(screen.getByRole('button'));
    expect(screen.getByText('EDITORIAL_NOTES')).toBeInTheDocument();

    await user.click(screen.getByRole('button'));
    expect(screen.queryByText('EDITORIAL_NOTES')).not.toBeInTheDocument();
  });

  it('applies compact styling when compact is true', () => {
    const { container } = render(
      <SectionNode section={section} titleNumber={17} compact />
    );
    const button = container.querySelector('button');
    expect(button?.className).toContain('text-xs');
  });

  it('shows amendment metadata when present', () => {
    render(<SectionNode section={sectionWithAmendment} titleNumber={17} />);
    expect(screen.getByText(/2020/)).toBeInTheDocument();
    expect(screen.getByText(/PL 116-283/)).toBeInTheDocument();
  });

  it('does not show amendment metadata when absent', () => {
    render(<SectionNode section={section} titleNumber={17} />);
    expect(screen.queryByText('PL')).not.toBeInTheDocument();
  });
});
