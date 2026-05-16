import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import RelatedBillsPanel from './RelatedBillsPanel';
import type { RelatedBill } from '@/lib/types';

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

const baseBill: RelatedBill = {
  congress: 113,
  bill_type: 'S',
  bill_number: 545,
  title: 'A related Senate bill',
  relationship_details: 'Identical bill',
  law_number: null,
};

describe('RelatedBillsPanel', () => {
  it('renders nothing when bills list is empty', () => {
    const { container } = render(<RelatedBillsPanel bills={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('links to Congress.gov when law_number is null', () => {
    render(<RelatedBillsPanel bills={[baseBill]} />);
    const link = screen.getByRole('link', { name: /S\. 545/ });
    expect(link.getAttribute('href')).toContain('congress.gov');
    expect(link.getAttribute('target')).toBe('_blank');
  });

  it('links internally when law_number is set', () => {
    const enactedBill: RelatedBill = { ...baseBill, law_number: 22 };
    render(<RelatedBillsPanel bills={[enactedBill]} />);
    const link = screen.getByRole('link', { name: /S\. 545/ });
    expect(link.getAttribute('href')).toBe('/laws/113/22');
    expect(link.getAttribute('target')).toBeNull();
  });

  it('renders bill title and relationship details', () => {
    render(<RelatedBillsPanel bills={[baseBill]} />);
    expect(screen.getByText('A related Senate bill')).toBeDefined();
    expect(screen.getByText('Identical bill')).toBeDefined();
  });
});
