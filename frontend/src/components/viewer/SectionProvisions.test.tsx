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

  it('applies hanging indent classes to content spans', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) First"
        isRepealed={false}
      />
    );
    // Provision content span has hanging indent and min-w-0 classes
    const provisionSpan = container.querySelector('.whitespace-pre-wrap');
    expect(provisionSpan).toHaveClass('pl-[4ch]', '-indent-[4ch]', 'min-w-0');

    // Provision flex container has items-start
    const provisionRow = provisionSpan!.closest('.flex');
    expect(provisionRow).toHaveClass('items-start');

    // Docstring content spans also have hanging indent
    const docstringSpan = screen.getByText('17 U.S.C. § 106').closest('span');
    expect(docstringSpan).toHaveClass('pl-[4ch]', '-indent-[4ch]', 'min-w-0');
  });

  it('splits leading whitespace into a separate indent span', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent={'(a) First\n\t\t(1) Nested'}
        isRepealed={false}
      />
    );
    // Leading whitespace is in a whitespace-pre span
    const indentSpan = container.querySelector('.whitespace-pre.shrink-0');
    expect(indentSpan).toBeInTheDocument();
    expect(indentSpan!.textContent).toBe('\t\t');

    // Text content (without leading whitespace) is in a whitespace-pre-wrap span
    expect(screen.getByText('(1) Nested')).toBeInTheDocument();
  });

  it('omits indent span when line has no leading whitespace', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) First"
        isRepealed={false}
      />
    );
    const indentSpan = container.querySelector('.whitespace-pre.shrink-0');
    expect(indentSpan).not.toBeInTheDocument();
  });

  it('applies header styling to short marker lines', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) In General"
        isRepealed={false}
      />
    );
    const headerSpan = screen.getByText('(a) In General');
    expect(headerSpan).toHaveClass('font-bold', 'text-blue-700');
    // Should still have hanging indent (it's also a list item)
    expect(headerSpan).toHaveClass('pl-[4ch]', '-indent-[4ch]');
  });

  it('does not apply header styling to long list items ending with punctuation', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="(1) forcibly assaults, resists, opposes, impedes, intimidates, or interferes with a person designated in section 1114;"
        isRepealed={false}
      />
    );
    const listItemSpan = screen.getByText(
      '(1) forcibly assaults, resists, opposes, impedes, intimidates, or interferes with a person designated in section 1114;'
    );
    expect(listItemSpan).not.toHaveClass('font-bold');
    expect(listItemSpan).toHaveClass('text-gray-800');
  });

  it('does not apply header styling to short list items ending with punctuation', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="(A) the armed forces;"
        isRepealed={false}
      />
    );
    const span = screen.getByText('(A) the armed forces;');
    expect(span).not.toHaveClass('font-bold');
    expect(span).toHaveClass('text-gray-800');
  });

  it('does not apply header styling to prose lines', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="Whoever knowingly does something."
        isRepealed={false}
      />
    );
    const span = screen.getByText('Whoever knowingly does something.');
    expect(span).not.toHaveClass('font-bold');
    expect(span).toHaveClass('text-gray-800');
  });

  it('does not apply hanging indent to prose lines', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent={'\tWhoever does something.'}
        isRepealed={false}
      />
    );
    const proseSpan = screen.getByText('Whoever does something.');
    expect(proseSpan).not.toHaveClass('pl-[4ch]');
    expect(proseSpan).not.toHaveClass('-indent-[4ch]');
    expect(proseSpan).toHaveClass('min-w-0', 'whitespace-pre-wrap');
  });
});
