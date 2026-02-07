import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SectionProvisions from './SectionProvisions';

describe('SectionProvisions', () => {
  it('renders text content in a pre block', () => {
    render(
      <SectionProvisions
        textContent="    (a) Test provision text"
        isRepealed={false}
      />
    );
    expect(screen.getByText('(a) Test provision text')).toBeInTheDocument();
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

  it('preserves indentation in rendered output', () => {
    const { container } = render(
      <SectionProvisions
        textContent={'(a) First\n    (1) Nested'}
        isRepealed={false}
      />
    );
    const pre = container.querySelector('pre');
    expect(pre).toBeInTheDocument();
    expect(pre?.textContent).toContain('(a) First\n    (1) Nested');
  });
});
