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
        enactedDate={null}
        lastModifiedDate={null}
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
        enactedDate={null}
        lastModifiedDate={null}
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
    render(
      <SectionHeader
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={true}
        status={null}
      />
    );
    expect(screen.getByText('Positive Law')).toBeInTheDocument();
  });

  it('shows Repealed badge when status is repealed', () => {
    render(
      <SectionHeader
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={false}
        status="repealed"
      />
    );
    expect(screen.getByText('Repealed')).toBeInTheDocument();
  });

  it('shows Reserved badge when status is reserved', () => {
    render(
      <SectionHeader
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={false}
        status="reserved"
      />
    );
    expect(screen.getByText('Reserved')).toBeInTheDocument();
  });

  it('shows Transferred badge when status is transferred', () => {
    render(
      <SectionHeader
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={false}
        status="transferred"
      />
    );
    expect(screen.getByText('Transferred')).toBeInTheDocument();
  });

  it('shows Renumbered badge when status is renumbered', () => {
    render(
      <SectionHeader
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={false}
        status="renumbered"
      />
    );
    expect(screen.getByText('Renumbered')).toBeInTheDocument();
  });

  it('shows Omitted badge when status is omitted', () => {
    render(
      <SectionHeader
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={false}
        status="omitted"
      />
    );
    expect(screen.getByText('Omitted')).toBeInTheDocument();
  });

  it('shows no status badge when status is null', () => {
    render(
      <SectionHeader
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={false}
        status={null}
      />
    );
    expect(screen.queryByText('Repealed')).not.toBeInTheDocument();
    expect(screen.queryByText('Reserved')).not.toBeInTheDocument();
    expect(screen.queryByText('Transferred')).not.toBeInTheDocument();
    expect(screen.queryByText('Renumbered')).not.toBeInTheDocument();
    expect(screen.queryByText('Omitted')).not.toBeInTheDocument();
  });

  it('shows enacted and last modified dates when provided', () => {
    render(
      <SectionHeader
        heading="Test"
        enactedDate="1976-10-19"
        lastModifiedDate="2020-01-01"
        isPositiveLaw={false}
        status={null}
      />
    );
    expect(screen.getByText('Enacted 1976-10-19')).toBeInTheDocument();
    expect(screen.getByText('Last modified 2020-01-01')).toBeInTheDocument();
  });

  it('hides dates when not provided', () => {
    render(
      <SectionHeader
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={false}
        status={null}
      />
    );
    expect(screen.queryByText(/Enacted/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Last modified/)).not.toBeInTheDocument();
  });

  it('renders latest amendment badge when provided', () => {
    render(
      <SectionHeader
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={false}
        status={null}
        latestAmendment={{ publicLawId: 'PL 116-283', year: 2021 }}
      />
    );
    expect(screen.getByText('PL 116-283')).toBeInTheDocument();
    expect(screen.getByText(/2021/)).toBeInTheDocument();
    expect(screen.getByText(/Last amended by/)).toBeInTheDocument();
  });
});
