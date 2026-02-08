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
  section_number: '909',
  heading: 'Mask work notice',
  sort_order: 3,
  note_categories: ['editorial'],
};

describe('SectionNode', () => {
  it('renders the heading as a link to the section directory', () => {
    render(<SectionNode section={section} titleNumber={17} />);
    const link = screen.getByRole('link', { name: 'Mask work notice' });
    expect(link).toHaveAttribute('href', '/sections/17/909');
  });

  it('shows section number as sub-header when expanded', async () => {
    const user = userEvent.setup();
    render(<SectionNode section={section} titleNumber={17} />);
    await user.click(screen.getByRole('button', { name: 'Expand' }));
    expect(screen.getByText(/§/)).toBeInTheDocument();
  });

  it('shows folder icon with expand/collapse toggle', () => {
    render(<SectionNode section={section} titleNumber={17} />);
    expect(screen.getByRole('button', { name: 'Expand' })).toBeInTheDocument();
  });

  it('expands to show code file and note files on icon click', async () => {
    const user = userEvent.setup();
    render(<SectionNode section={section} titleNumber={17} />);

    await user.click(screen.getByRole('button', { name: 'Expand' }));

    const links = screen.getAllByRole('link');
    const codeLink = links.find(
      (l) => l.getAttribute('href') === '/sections/17/909/CODE'
    );
    expect(codeLink).toBeDefined();
    expect(
      screen.getByRole('link', { name: 'EDITORIAL_NOTES' })
    ).toHaveAttribute('href', '/sections/17/909/EDITORIAL_NOTES');
    // STATUTORY_NOTES not in note_categories, so not shown
    expect(screen.queryByText('STATUTORY_NOTES')).not.toBeInTheDocument();
  });

  it('auto-expands when isActive', () => {
    render(<SectionNode section={section} titleNumber={17} isActive />);
    expect(
      screen.getByRole('link', { name: 'EDITORIAL_NOTES' })
    ).toBeInTheDocument();
  });

  it('applies active styling when isActive', () => {
    const { container } = render(
      <SectionNode section={section} titleNumber={17} isActive />
    );
    const row = container.querySelector('.bg-primary-50');
    expect(row).toBeInTheDocument();
  });
});
