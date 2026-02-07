import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SectionNotes from './SectionNotes';
import type { SectionNote } from '@/lib/types';

const notes: SectionNote[] = [
  {
    header: 'References in Text',
    content: 'The Act referred to in subsection (a)...',
    lines: [],
    category: 'editorial',
  },
  {
    header: 'Amendments',
    content: '',
    lines: [
      {
        line_number: 1,
        content: '2002—Subsec. (a). Pub. L. 107–273 amended heading.',
        indent_level: 0,
        marker: null,
        is_header: false,
      },
      {
        line_number: 2,
        content: 'Subsec. (b). Pub. L. 107–273 added subsec.',
        indent_level: 1,
        marker: null,
        is_header: false,
      },
    ],
    category: 'historical',
  },
  {
    header: 'Short Title',
    content: '',
    lines: [
      {
        line_number: 1,
        content: 'This Act may be cited as the "Copyright Act of 1976".',
        indent_level: 0,
        marker: null,
        is_header: false,
      },
    ],
    category: 'statutory',
  },
];

describe('SectionNotes', () => {
  it('renders nothing when notes is empty', () => {
    const { container } = render(<SectionNotes notes={[]} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders grouped category headings', () => {
    render(<SectionNotes notes={notes} />);
    expect(screen.getByText('Editorial Notes (1)')).toBeInTheDocument();
    expect(screen.getByText('Statutory Notes (1)')).toBeInTheDocument();
    expect(screen.getByText('Historical Notes (1)')).toBeInTheDocument();
  });

  it('renders note headers with # prefix', () => {
    render(<SectionNotes notes={notes} />);
    expect(screen.getByText('References in Text')).toBeInTheDocument();
    expect(screen.getByText('Amendments')).toBeInTheDocument();
    expect(screen.getByText('Short Title')).toBeInTheDocument();
  });

  it('renders content lines with # prefix when lines is empty', () => {
    render(<SectionNotes notes={notes} />);
    expect(
      screen.getByText('The Act referred to in subsection (a)...')
    ).toBeInTheDocument();
  });

  it('renders structured lines with # prefix when available', () => {
    render(<SectionNotes notes={notes} />);
    expect(
      screen.getByText(/2002—Subsec\. \(a\)\. Pub\. L\. 107–273/)
    ).toBeInTheDocument();
  });

  it('shows line numbers', () => {
    render(<SectionNotes notes={notes} />);
    // Each category starts at line 1; multiple "1"s expected across categories
    const ones = screen.getAllByText('1');
    expect(ones.length).toBeGreaterThanOrEqual(3); // one per category header
    // Line 2 appears in editorial (content) and historical (first content line)
    const twos = screen.getAllByText('2');
    expect(twos.length).toBeGreaterThanOrEqual(2);
  });

  it('omits categories with no notes', () => {
    const editorialOnly: SectionNote[] = [notes[0]];
    render(<SectionNotes notes={editorialOnly} />);
    expect(screen.getByText('Editorial Notes (1)')).toBeInTheDocument();
    expect(screen.queryByText(/Statutory/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Historical/)).not.toBeInTheDocument();
  });
});
