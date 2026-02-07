import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import CitationList from './CitationList';
import type { SourceLaw } from '@/lib/types';

const citations: SourceLaw[] = [
  {
    law_id: 'PL 94-553',
    law_title: 'Copyright Act of 1976',
    relationship: 'Enactment',
    raw_text: 'Oct. 19, 1976, Pub. L. 94-553, title I, § 106, 90 Stat. 2546',
  },
  {
    law_id: 'PL 107-273',
    law_title: null,
    relationship: 'Amendment',
    raw_text: 'Nov. 2, 2002, Pub. L. 107-273',
  },
];

describe('CitationList', () => {
  it('renders nothing when citations is empty', () => {
    const { container } = render(<CitationList citations={[]} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders Source Laws heading', () => {
    render(<CitationList citations={citations} />);
    expect(screen.getByText('Source Laws')).toBeInTheDocument();
  });

  it('renders law IDs', () => {
    render(<CitationList citations={citations} />);
    expect(screen.getByText('PL 94-553')).toBeInTheDocument();
    expect(screen.getByText('PL 107-273')).toBeInTheDocument();
  });

  it('renders relationship badges', () => {
    render(<CitationList citations={citations} />);
    expect(screen.getByText('Enactment')).toBeInTheDocument();
    expect(screen.getByText('Amendment')).toBeInTheDocument();
  });

  it('renders raw citation text', () => {
    render(<CitationList citations={citations} />);
    expect(screen.getByText(/Oct\. 19, 1976/)).toBeInTheDocument();
  });
});
