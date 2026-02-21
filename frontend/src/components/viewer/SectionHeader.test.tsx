import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import SectionHeader from './SectionHeader';

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

describe('SectionHeader', () => {
  it('renders heading as the page title', () => {
    render(
      <SectionHeader
        heading="Exclusive rights in copyrighted works"
        isPositiveLaw={false}
        status={null}
      />
    );
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Exclusive rights in copyrighted works'
    );
  });

  it('renders breadcrumbs as subtitle', () => {
    render(
      <SectionHeader
        heading="Exclusive rights"
        breadcrumbs={[
          { label: 'Title 17', href: '/titles/17' },
          { label: 'Chapter 1', href: '/titles/17/chapters/1' },
          { label: '\u00A7\u2009106' },
        ]}
        isPositiveLaw={false}
        status={null}
      />
    );
    expect(screen.getByRole('link', { name: 'Title 17' })).toHaveAttribute(
      'href',
      '/titles/17'
    );
    expect(screen.getByRole('link', { name: 'Chapter 1' })).toHaveAttribute(
      'href',
      '/titles/17/chapters/1'
    );
    expect(screen.getByText(/§/)).toBeInTheDocument();
  });

  it('shows Positive Law badge when isPositiveLaw is true', () => {
    render(<SectionHeader heading="Test" isPositiveLaw={true} status={null} />);
    expect(screen.getByText('Positive Law')).toBeInTheDocument();
  });

  it('shows Repealed badge when status is repealed', () => {
    render(
      <SectionHeader heading="Test" isPositiveLaw={false} status="repealed" />
    );
    expect(screen.getByText('Repealed')).toBeInTheDocument();
  });

  it('shows Reserved badge when status is reserved', () => {
    render(
      <SectionHeader heading="Test" isPositiveLaw={false} status="reserved" />
    );
    expect(screen.getByText('Reserved')).toBeInTheDocument();
  });

  it('shows Transferred badge when status is transferred', () => {
    render(
      <SectionHeader
        heading="Test"
        isPositiveLaw={false}
        status="transferred"
      />
    );
    expect(screen.getByText('Transferred')).toBeInTheDocument();
  });

  it('shows Renumbered badge when status is renumbered', () => {
    render(
      <SectionHeader heading="Test" isPositiveLaw={false} status="renumbered" />
    );
    expect(screen.getByText('Renumbered')).toBeInTheDocument();
  });

  it('shows Omitted badge when status is omitted', () => {
    render(
      <SectionHeader heading="Test" isPositiveLaw={false} status="omitted" />
    );
    expect(screen.getByText('Omitted')).toBeInTheDocument();
  });

  it('shows no status badge when status is null', () => {
    render(
      <SectionHeader heading="Test" isPositiveLaw={false} status={null} />
    );
    expect(screen.queryByText('Repealed')).not.toBeInTheDocument();
    expect(screen.queryByText('Reserved')).not.toBeInTheDocument();
    expect(screen.queryByText('Transferred')).not.toBeInTheDocument();
    expect(screen.queryByText('Renumbered')).not.toBeInTheDocument();
    expect(screen.queryByText('Omitted')).not.toBeInTheDocument();
  });

  it('renders enacted and last amended law info', () => {
    render(
      <SectionHeader
        heading="Test"
        isPositiveLaw={false}
        status={null}
        enacted={{
          congress: 93,
          lawNumber: 406,
          date: '1974-09-02',
          label: 'PL 93-406',
        }}
        lastAmended={{
          congress: 113,
          lawNumber: 22,
          date: '2013-07-25',
          label: 'PL 113-22',
        }}
      />
    );
    expect(screen.getByText('Enacted:')).toBeInTheDocument();
    expect(screen.getByText('93rd Congress')).toBeInTheDocument();
    expect(screen.getByText('PL 93-406')).toBeInTheDocument();
    expect(screen.getByText('Last amended:')).toBeInTheDocument();
    expect(screen.getByText('113th Congress')).toBeInTheDocument();
    expect(screen.getByText('PL 113-22')).toBeInTheDocument();
  });

  it('hides law info when not provided', () => {
    render(
      <SectionHeader heading="Test" isPositiveLaw={false} status={null} />
    );
    expect(screen.queryByText(/Enacted/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Last amended/)).not.toBeInTheDocument();
  });

  it('shows only enacted when no amendments exist', () => {
    render(
      <SectionHeader
        heading="Test"
        isPositiveLaw={false}
        status={null}
        enacted={{
          congress: 93,
          lawNumber: 406,
          date: '1974-09-02',
          label: 'PL 93-406',
        }}
      />
    );
    expect(screen.getByText('Enacted:')).toBeInTheDocument();
    expect(screen.getByText('PL 93-406')).toBeInTheDocument();
    expect(screen.queryByText(/Last amended/)).not.toBeInTheDocument();
  });

  it('handles prose date format without showing Invalid Date', () => {
    render(
      <SectionHeader
        heading="Test"
        isPositiveLaw={false}
        status={null}
        enacted={{
          congress: 93,
          lawNumber: 406,
          date: 'Sept. 2, 1974',
          label: 'PL 93-406',
        }}
      />
    );
    expect(screen.queryByText(/Invalid Date/)).not.toBeInTheDocument();
    expect(screen.getByText(/1974/)).toBeInTheDocument();
  });

  it('renders short title after PL ID when provided', () => {
    render(
      <SectionHeader
        heading="Test"
        isPositiveLaw={false}
        status={null}
        enacted={{
          congress: 93,
          lawNumber: 406,
          date: '1974-09-02',
          label: 'PL 93-406',
          shortTitle: 'Employee Retirement Income Security Act of 1974',
        }}
      />
    );
    expect(
      screen.getByText('Employee Retirement Income Security Act of 1974')
    ).toBeInTheDocument();
  });
});
