import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import AmendmentList from './AmendmentList';
import type { Amendment } from '@/lib/types';

const amendments: Amendment[] = [
  {
    law: {
      congress: 107,
      law_number: 273,
      public_law_id: 'PL 107-273',
      date: '2002-11-02',
    },
    year: 2002,
    description: 'Amended subsection (a)',
    public_law_id: 'PL 107-273',
  },
  {
    law: {
      congress: 116,
      law_number: 283,
      public_law_id: 'PL 116-283',
      date: '2021-01-01',
    },
    year: 2021,
    description: 'Added subsection (c)',
    public_law_id: 'PL 116-283',
  },
  {
    law: {
      congress: 116,
      law_number: 260,
      public_law_id: 'PL 116-260',
      date: '2021-12-27',
    },
    year: 2021,
    description: 'Technical correction',
    public_law_id: 'PL 116-260',
  },
];

describe('AmendmentList', () => {
  it('renders nothing when amendments is empty', () => {
    const { container } = render(<AmendmentList amendments={[]} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders amendment history heading', () => {
    render(<AmendmentList amendments={amendments} />);
    expect(screen.getByText('Amendment History')).toBeInTheDocument();
  });

  it('groups amendments by year, newest first', () => {
    render(<AmendmentList amendments={amendments} />);
    const yearHeaders = screen.getAllByRole('heading', { level: 4 });
    expect(yearHeaders[0]).toHaveTextContent('2021');
    expect(yearHeaders[1]).toHaveTextContent('2002');
  });

  it('renders all amendment entries', () => {
    render(<AmendmentList amendments={amendments} />);
    expect(screen.getByText('PL 107-273')).toBeInTheDocument();
    expect(screen.getByText('PL 116-283')).toBeInTheDocument();
    expect(screen.getByText('PL 116-260')).toBeInTheDocument();
  });

  it('shows descriptions', () => {
    render(<AmendmentList amendments={amendments} />);
    expect(screen.getByText('Amended subsection (a)')).toBeInTheDocument();
    expect(screen.getByText('Added subsection (c)')).toBeInTheDocument();
  });
});
