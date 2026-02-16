import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SectionProvisions from './SectionProvisions';

const defaultProps = {
  fullCitation: '17 U.S.C. § 106',
  heading: 'Exclusive rights in copyrighted works',
  provisions: null as null,
};

describe('SectionProvisions', () => {
  it('renders docstring comment lines at the top', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) Test provision text"
        status={null}
      />
    );
    expect(screen.getByText('17 U.S.C. § 106')).toBeInTheDocument();
    expect(
      screen.getByText('Exclusive rights in copyrighted works')
    ).toBeInTheDocument();
    expect(screen.getByText('Provisions')).toBeInTheDocument();
  });

  it('numbers docstring as lines 1–3, blank line 4, provisions from line 5', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) First"
        status={null}
      />
    );
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('renders text content with line numbers', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="    (a) Test provision text;"
        status={null}
      />
    );
    expect(screen.getByText('(a) Test provision text;')).toBeInTheDocument();
  });

  it('shows repealed notice when text is null and section is repealed', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent={null}
        status="repealed"
      />
    );
    expect(
      screen.getByText('This section has been repealed.')
    ).toBeInTheDocument();
  });

  it('shows reserved notice when text is null and section is reserved', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent={null}
        status="reserved"
      />
    );
    expect(
      screen.getByText('This section is reserved for future use.')
    ).toBeInTheDocument();
  });

  it('shows transferred notice when text is null and section is transferred', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent={null}
        status="transferred"
      />
    );
    expect(
      screen.getByText('This section has been transferred.')
    ).toBeInTheDocument();
  });

  it('shows renumbered notice when text is null and section is renumbered', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent={null}
        status="renumbered"
      />
    );
    expect(
      screen.getByText('This section has been renumbered.')
    ).toBeInTheDocument();
  });

  it('shows omitted notice when text is null and section is omitted', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent={null}
        status="omitted"
      />
    );
    expect(
      screen.getByText('This section has been editorially omitted.')
    ).toBeInTheDocument();
  });

  it('shows generic notice when text is null and section is active', () => {
    render(
      <SectionProvisions {...defaultProps} textContent={null} status={null} />
    );
    expect(
      screen.getByText('No text content available for this section.')
    ).toBeInTheDocument();
  });

  it('renders each provision line with its own line number', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent={'(a) First provision;\n    (1) Nested item;'}
        status={null}
      />
    );
    // Lines 1–3 are docstring, 4 is blank, 5–6 are provisions
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('6')).toBeInTheDocument();
    expect(screen.getByText('(a) First provision;')).toBeInTheDocument();
    expect(screen.getByText('(1) Nested item;')).toBeInTheDocument();
  });

  it('applies hanging indent classes to content spans', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) First"
        status={null}
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
    expect(docstringSpan).toHaveClass('pl-[2ch]', '-indent-[2ch]', 'min-w-0');
  });

  it('splits leading whitespace into a separate indent span', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent={'(a) First provision;\n\t\t(1) Nested item;'}
        status={null}
      />
    );
    // Leading whitespace is in a whitespace-pre span
    const indentSpan = container.querySelector('.whitespace-pre.shrink-0');
    expect(indentSpan).toBeInTheDocument();
    expect(indentSpan!.textContent).toBe('\t\t');

    // Text content (without leading whitespace) is in a whitespace-pre-wrap span
    expect(screen.getByText('(1) Nested item;')).toBeInTheDocument();
  });

  it('omits indent span when line has no leading whitespace', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) First"
        status={null}
      />
    );
    const indentSpan = container.querySelector('.whitespace-pre.shrink-0');
    expect(indentSpan).not.toBeInTheDocument();
  });

  it('applies split header styling to short marker lines', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) In General"
        status={null}
      />
    );
    // Marker and title are split into separate spans
    const markerSpan = container.querySelector('.text-primary-600');
    expect(markerSpan).toBeInTheDocument();
    expect(markerSpan!.textContent).toBe('(a) ');
    expect(markerSpan).not.toHaveClass('font-bold');

    const titleSpan = screen.getByText('In General');
    expect(titleSpan).toHaveClass('font-bold', 'text-primary-700');

    // Outer span should still have hanging indent (it's also a list item)
    const outerSpan = markerSpan!.closest('.whitespace-pre-wrap');
    expect(outerSpan).toHaveClass('pl-[4ch]', '-indent-[4ch]');

    // Header row should be sticky with top and z-index set via inline style
    const headerRow = markerSpan!.closest('.flex');
    expect(headerRow).toHaveClass('sticky', 'bg-gray-100');
    expect((headerRow as HTMLElement).style.top).toBe('0em');
    expect((headerRow as HTMLElement).style.zIndex).toBe('20');

    // Border only appears when stuck (via IntersectionObserver), not by default
    expect(headerRow).not.toHaveClass('border-b');
  });

  it('renders sentinel elements before sticky headers', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) In General"
        status={null}
      />
    );
    const sentinel = container.querySelector('[data-sticky-sentinel]');
    expect(sentinel).toBeInTheDocument();
    expect(sentinel).toHaveClass('h-0');
    expect(sentinel).toHaveAttribute('aria-hidden', 'true');
  });

  it('does not render sentinels for non-header lines', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent="(1) forcibly assaults, resists, opposes, impedes;"
        status={null}
      />
    );
    const sentinel = container.querySelector('[data-sticky-sentinel]');
    expect(sentinel).not.toBeInTheDocument();
  });

  it('stacks nested headers with increasing top offsets', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent={'(a) In General\n    (1) First Rule\n        (A) Sub Rule'}
        status={null}
      />
    );
    const headers = container.querySelectorAll('[data-sticky-header]');
    expect(headers).toHaveLength(3);

    // Each depth level gets a progressively larger top offset
    expect((headers[0] as HTMLElement).style.top).toBe('0em');
    expect((headers[1] as HTMLElement).style.top).toBe('1.625em');
    expect((headers[2] as HTMLElement).style.top).toBe('3.25em');

    // All are sticky with decreasing z-index (parents above children)
    expect(headers[0]).toHaveClass('sticky');
    expect(headers[1]).toHaveClass('sticky');
    expect(headers[2]).toHaveClass('sticky');
    expect((headers[0] as HTMLElement).style.zIndex).toBe('20');
    expect((headers[1] as HTMLElement).style.zIndex).toBe('19');
    expect((headers[2] as HTMLElement).style.zIndex).toBe('18');
  });

  it('wraps sections so nested headers unstick with their parent', () => {
    const { container } = render(
      <SectionProvisions
        {...defaultProps}
        textContent={'(a) First\n    (1) Nested\n(b) Second'}
        status={null}
      />
    );
    const headerA = container.querySelector('[data-sticky-header="0"]');
    const header1 = container.querySelector('[data-sticky-header="1"]');
    const headerB = container.querySelector('[data-sticky-header="2"]');

    // (1) is nested inside (a)'s wrapper div
    const wrapperA = headerA!.parentElement;
    expect(wrapperA).toContainElement(header1 as HTMLElement);

    // (b) is NOT inside (a)'s wrapper
    expect(wrapperA).not.toContainElement(headerB as HTMLElement);
  });

  it('does not apply header styling to long list items ending with punctuation', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="(1) forcibly assaults, resists, opposes, impedes, intimidates, or interferes with a person designated in section 1114;"
        status={null}
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
        status={null}
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
        status={null}
      />
    );
    const span = screen.getByText('Whoever knowingly does something.');
    expect(span).not.toHaveClass('font-bold');
    expect(span).toHaveClass('text-gray-800');
  });

  it('does not apply header styling to lines ending with em dash', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="(b) Whoever willfully—"
        status={null}
      />
    );
    const span = screen.getByText('(b) Whoever willfully—');
    expect(span).not.toHaveClass('font-bold');
    expect(span).toHaveClass('text-gray-800');
  });

  it('does not apply header styling to lines ending with trailing "or"', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="(C) a foreign official; or"
        status={null}
      />
    );
    const span = screen.getByText('(C) a foreign official; or');
    expect(span).not.toHaveClass('font-bold');
    expect(span).toHaveClass('text-gray-800');
  });

  it('does not apply header styling to lines ending with trailing "and"', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="(2) in any other case; and"
        status={null}
      />
    );
    const span = screen.getByText('(2) in any other case; and');
    expect(span).not.toHaveClass('font-bold');
    expect(span).toHaveClass('text-gray-800');
  });

  it('does not apply hanging indent to prose lines', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent={'\tWhoever does something.'}
        status={null}
      />
    );
    const proseSpan = screen.getByText('Whoever does something.');
    expect(proseSpan).not.toHaveClass('pl-[4ch]');
    expect(proseSpan).not.toHaveClass('-indent-[4ch]');
    expect(proseSpan).toHaveClass('min-w-0', 'whitespace-pre-wrap');
  });

  it('falls back to text_content parsing when provisions is null', () => {
    render(
      <SectionProvisions
        {...defaultProps}
        textContent="(a) In General"
        provisions={null}
        status={null}
      />
    );
    // Legacy heuristic should still detect header
    const titleSpan = screen.getByText('In General');
    expect(titleSpan).toHaveClass('font-bold', 'text-primary-700');
  });
});

describe('SectionProvisions with structured provisions', () => {
  const baseProps = {
    fullCitation: '18 U.S.C. § 112',
    heading: 'Protection of foreign officials',
    textContent: '(a) In General\n\tWhoever assaults...',
    status: null as null,
  };

  it('applies header styling when is_header is true', () => {
    render(
      <SectionProvisions
        {...baseProps}
        provisions={[
          {
            line_number: 1,
            content: '(a) In General',
            indent_level: 0,
            marker: '(a)',
            is_header: true,
          },
          {
            line_number: 2,
            content: 'Whoever assaults...',
            indent_level: 1,
            marker: null,
            is_header: false,
          },
        ]}
      />
    );
    const titleSpan = screen.getByText('In General');
    expect(titleSpan).toHaveClass('font-bold', 'text-primary-700');
  });

  it('does not apply header styling when is_header is false even for short marker lines', () => {
    render(
      <SectionProvisions
        {...baseProps}
        provisions={[
          {
            line_number: 1,
            content: '(b) Whoever willfully—',
            indent_level: 0,
            marker: '(b)',
            is_header: false,
          },
        ]}
      />
    );
    const span = screen.getByText('(b) Whoever willfully—');
    expect(span).not.toHaveClass('font-bold');
    expect(span).toHaveClass('text-gray-800');
  });

  it('does not apply header styling to non-header list items', () => {
    render(
      <SectionProvisions
        {...baseProps}
        provisions={[
          {
            line_number: 1,
            content: '(C) a foreign official; or',
            indent_level: 2,
            marker: '(C)',
            is_header: false,
          },
        ]}
      />
    );
    const span = screen.getByText('(C) a foreign official; or');
    expect(span).not.toHaveClass('font-bold');
    expect(span).toHaveClass('text-gray-800');
  });

  it('uses indent_level for indentation', () => {
    const { container } = render(
      <SectionProvisions
        {...baseProps}
        provisions={[
          {
            line_number: 1,
            content: 'Nested content',
            indent_level: 2,
            marker: null,
            is_header: false,
          },
        ]}
      />
    );
    const indentSpan = container.querySelector('.whitespace-pre.shrink-0');
    expect(indentSpan).toBeInTheDocument();
    expect(indentSpan!.textContent).toBe('\t\t');
  });

  it('renders sticky header for provisions-driven header lines', () => {
    const { container } = render(
      <SectionProvisions
        {...baseProps}
        provisions={[
          {
            line_number: 1,
            content: '(a) Definitions',
            indent_level: 0,
            marker: '(a)',
            is_header: true,
          },
        ]}
      />
    );
    const stickyHeader = container.querySelector('[data-sticky-header]');
    expect(stickyHeader).toBeInTheDocument();
    expect(stickyHeader).toHaveClass('sticky');
  });
});
