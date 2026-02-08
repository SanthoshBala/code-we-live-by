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
  it('renders the section number and heading as a link', () => {
    render(<SectionNode section={section} titleNumber={17} />);
    const link = screen.getByRole('link', { name: /909/ });
    expect(link).toHaveAttribute('href', '/sections/17/909');
    expect(screen.getByText('Mask work notice')).toBeInTheDocument();
  });

  it('shows folder icon with expand/collapse toggle', () => {
    render(<SectionNode section={section} titleNumber={17} />);
    expect(
      screen.getByRole('button', { name: 'Expand' })
    ).toBeInTheDocument();
  });

  it('expands to show CODE and note files on icon click', async () => {
    const user = userEvent.setup();
    render(<SectionNode section={section} titleNumber={17} />);

    await user.click(screen.getByRole('button', { name: 'Expand' }));

    expect(screen.getByRole('link', { name: 'CODE' })).toHaveAttribute(
      'href',
      '/sections/17/909/CODE'
    );
    expect(
      screen.getByRole('link', { name: 'EDITORIAL_NOTES' })
    ).toHaveAttribute('href', '/sections/17/909/EDITORIAL_NOTES');
    // STATUTORY_NOTES not in note_categories, so not shown
    expect(screen.queryByText('STATUTORY_NOTES')).not.toBeInTheDocument();
  });

  it('auto-expands when isActive', () => {
    render(<SectionNode section={section} titleNumber={17} isActive />);
    expect(screen.getByRole('link', { name: 'CODE' })).toBeInTheDocument();
  });

  it('applies active styling when isActive', () => {
    const { container } = render(
      <SectionNode section={section} titleNumber={17} isActive />
    );
    const row = container.querySelector('.bg-primary-50');
    expect(row).toBeInTheDocument();
  });
});
