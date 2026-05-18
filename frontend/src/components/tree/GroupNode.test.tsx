import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import GroupNode from './GroupNode';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

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

const group = {
  group_type: 'chapter',
  number: '1',
  name: 'Subject Matter and Scope of Copyright',
  sort_order: 1,
  children: [
    {
      group_type: 'subchapter',
      number: 'A',
      name: 'The Works',
      sort_order: 1,
      children: [],
      sections: [
        { section_number: '101', heading: 'Definitions', sort_order: 1 },
      ],
    },
  ],
  sections: [
    { section_number: '102', heading: 'Subject matter', sort_order: 2 },
  ],
};

describe('GroupNode', () => {
  it('renders the group name as a link', () => {
    render(
      <GroupNode group={group} titleNumber={17} parentPath="/titles/17" />,
      { wrapper }
    );
    const link = screen.getByRole('link', {
      name: /Subject Matter and Scope of Copyright/,
    });
    expect(link).toHaveAttribute('href', '/titles/17/chapter/1');
  });

  it('does not show children until expanded', () => {
    render(
      <GroupNode group={group} titleNumber={17} parentPath="/titles/17" />,
      { wrapper }
    );
    expect(screen.queryByText('Subject matter')).not.toBeInTheDocument();
  });

  it('icon click expands to show children', async () => {
    const user = userEvent.setup();
    render(
      <GroupNode group={group} titleNumber={17} parentPath="/titles/17" />,
      { wrapper }
    );
    await user.click(screen.getByRole('button', { name: 'Expand' }));
    expect(screen.getByText(/The Works/)).toBeInTheDocument();
    expect(screen.getByText('Subject matter')).toBeInTheDocument();
  });

  it('icon click collapses children', async () => {
    const user = userEvent.setup();
    render(
      <GroupNode group={group} titleNumber={17} parentPath="/titles/17" />,
      { wrapper }
    );
    await user.click(screen.getByRole('button', { name: 'Expand' }));
    expect(screen.getByText('Subject matter')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Collapse' }));
    expect(screen.queryByText('Subject matter')).not.toBeInTheDocument();
  });

  it('sections render as links to section viewer', async () => {
    const user = userEvent.setup();
    render(
      <GroupNode group={group} titleNumber={17} parentPath="/titles/17" />,
      { wrapper }
    );
    await user.click(screen.getByRole('button', { name: 'Expand' }));
    const sectionLink = screen.getByRole('link', { name: /Subject matter/ });
    expect(sectionLink).toHaveAttribute('href', '/sections/17/102');
  });
});
