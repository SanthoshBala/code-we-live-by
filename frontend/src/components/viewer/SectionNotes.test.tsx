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
];

const defaultProps = {
  notes,
  fullCitation: '17 U.S.C. § 909',
  heading: 'Mask work notice',
  categoryLabel: 'Editorial Notes',
};

describe('SectionNotes', () => {
  it('renders nothing when notes is empty', () => {
    const { container } = render(
      <SectionNotes
        notes={[]}
        fullCitation="17 U.S.C. § 909"
        heading="Mask work notice"
        categoryLabel="Editorial Notes"
      />
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders docstring comment lines at the top', () => {
    render(<SectionNotes {...defaultProps} />);
    expect(screen.getByText('17 U.S.C. § 909')).toBeInTheDocument();
    expect(screen.getByText('Mask work notice')).toBeInTheDocument();
    expect(screen.getByText('Editorial Notes')).toBeInTheDocument();
  });

  it('renders docstring lines with green comment styling', () => {
    const { container } = render(<SectionNotes {...defaultProps} />);
    const greenLines = container.querySelectorAll('.text-green-700');
    expect(greenLines.length).toBe(3);
  });

  it('renders a blank line after docstring', () => {
    render(<SectionNotes {...defaultProps} />);
    // Docstring lines 1–3, blank line 4
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('renders note headers', () => {
    render(<SectionNotes {...defaultProps} />);
    expect(screen.getByText('References in Text')).toBeInTheDocument();
    expect(screen.getByText('Amendments')).toBeInTheDocument();
  });

  it('renders content lines', () => {
    render(<SectionNotes {...defaultProps} />);
    expect(
      screen.getByText('The Act referred to in subsection (a)...')
    ).toBeInTheDocument();
  });

  it('renders structured lines when available', () => {
    render(<SectionNotes {...defaultProps} />);
    expect(
      screen.getByText(/2002—Subsec\. \(a\)\. Pub\. L\. 107–273/)
    ).toBeInTheDocument();
  });

  it('shows line numbers starting after docstring', () => {
    render(<SectionNotes {...defaultProps} />);
    // Line 1 is first docstring, line 5 is first note header
    const ones = screen.getAllByText('1');
    expect(ones.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('renders in a code-style block', () => {
    const { container } = render(<SectionNotes {...defaultProps} />);
    expect(container.querySelector('.bg-gray-100')).toBeInTheDocument();
  });

  it('does not use dropdown details/summary elements', () => {
    const { container } = render(<SectionNotes {...defaultProps} />);
    expect(container.querySelector('details')).toBeNull();
    expect(container.querySelector('summary')).toBeNull();
  });
});
