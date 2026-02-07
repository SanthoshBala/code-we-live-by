import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SectionProvisions from './SectionProvisions';

describe('SectionProvisions', () => {
  it('renders text content with line numbers', () => {
    render(
      <SectionProvisions
        textContent="    (a) Test provision text"
        isRepealed={false}
      />
    );
    expect(screen.getByText('(a) Test provision text')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows repealed notice when text is null and section is repealed', () => {
    render(<SectionProvisions textContent={null} isRepealed={true} />);
    expect(
      screen.getByText('This section has been repealed.')
    ).toBeInTheDocument();
  });

  it('shows generic notice when text is null and section is not repealed', () => {
    render(<SectionProvisions textContent={null} isRepealed={false} />);
    expect(
      screen.getByText('No text content available for this section.')
    ).toBeInTheDocument();
  });

  it('renders each line with its own line number', () => {
    render(
      <SectionProvisions
        textContent={'(a) First\n    (1) Nested'}
        isRepealed={false}
      />
    );
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('(a) First')).toBeInTheDocument();
    expect(screen.getByText('(1) Nested')).toBeInTheDocument();
  });

  it('preserves leading whitespace on each line', () => {
    const { container } = render(
      <SectionProvisions
        textContent={'(a) First\n    (1) Nested'}
        isRepealed={false}
      />
    );
    const spans = container.querySelectorAll('.whitespace-pre-wrap');
    expect(spans[1]?.textContent).toBe('    (1) Nested');
  });
});
