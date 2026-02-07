import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SectionProvisions from './SectionProvisions';

const defaultProps = {
  fullCitation: '17 U.S.C. § 106',
  heading: 'Exclusive rights in copyrighted works',
};

describe('SectionProvisions', () => {
  it('renders docstring comment lines at the top', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) Test provision text"
        isRepealed={false}
      />
    );
    expect(screen.getByText('17 U.S.C. § 106')).toBeInTheDocument();
    expect(
      screen.getByText('Exclusive rights in copyrighted works')
    ).toBeInTheDocument();
  });

  it('numbers docstring as lines 1–2, blank line 3, provisions from line 4', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) First"
        isRepealed={false}
      />
    );
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('renders text content with line numbers', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="    (a) Test provision text"
        isRepealed={false}
      />
    );
    expect(screen.getByText('(a) Test provision text')).toBeInTheDocument();
  });

  it('shows repealed notice when text is null and section is repealed', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent={null}
        isRepealed={true}
      />
    );
    expect(
      screen.getByText('This section has been repealed.')
    ).toBeInTheDocument();
  });

  it('shows generic notice when text is null and section is not repealed', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent={null}
        isRepealed={false}
      />
    );
    expect(
      screen.getByText('No text content available for this section.')
    ).toBeInTheDocument();
  });

  it('renders each provision line with its own line number', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent={'(a) First\n    (1) Nested'}
        isRepealed={false}
      />
    );
    // Lines 1–2 are docstring, 3 is blank, 4–5 are provisions
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('(a) First')).toBeInTheDocument();
    expect(screen.getByText('(1) Nested')).toBeInTheDocument();
  });

  it('preserves leading whitespace on each line', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent={'(a) First\n    (1) Nested'}
        isRepealed={false}
      />
    );
    const spans = container.querySelectorAll('.whitespace-pre-wrap');
    expect(spans[1]?.textContent).toBe('    (1) Nested');
  });
});
