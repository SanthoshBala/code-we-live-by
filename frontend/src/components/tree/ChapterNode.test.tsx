import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { TreeDisplayProvider } from '@/contexts/TreeDisplayContext';
import ChapterNode from './ChapterNode';

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

const chapter = {
  chapter_number: '1',
  chapter_name: 'Subject Matter and Scope of Copyright',
  sort_order: 1,
  subchapters: [
    {
      subchapter_number: 'A',
      subchapter_name: 'The Works',
      sort_order: 1,
      sections: [
        { section_number: '101', heading: 'Definitions', sort_order: 1 },
      ],
    },
  ],
  sections: [
    { section_number: '102', heading: 'Subject matter', sort_order: 2 },
  ],
};

function wrapper({ children }: { children: React.ReactNode }) {
  return <TreeDisplayProvider>{children}</TreeDisplayProvider>;
}

describe('ChapterNode', () => {
  it('renders the chapter name', () => {
    render(<ChapterNode chapter={chapter} titleNumber={17} />, { wrapper });
    expect(
      screen.getByText(/Subject Matter and Scope of Copyright/)
    ).toBeInTheDocument();
  });

  it('does not show children until expanded', () => {
    render(<ChapterNode chapter={chapter} titleNumber={17} />, { wrapper });
    expect(screen.queryByText('Subject matter')).not.toBeInTheDocument();
  });

  it('shows subchapters and sections when expanded', async () => {
    const user = userEvent.setup();
    render(<ChapterNode chapter={chapter} titleNumber={17} />, { wrapper });
    await user.click(screen.getByText(/Subject Matter and Scope of Copyright/));
    expect(screen.getByText(/The Works/)).toBeInTheDocument();
    expect(screen.getByText('Subject matter')).toBeInTheDocument();
  });

  it('collapses on second click', async () => {
    const user = userEvent.setup();
    render(<ChapterNode chapter={chapter} titleNumber={17} />, { wrapper });
    const button = screen.getByText(/Subject Matter and Scope of Copyright/);
    await user.click(button);
    expect(screen.getByText('Subject matter')).toBeInTheDocument();
    await user.click(button);
    expect(screen.queryByText('Subject matter')).not.toBeInTheDocument();
  });
});
