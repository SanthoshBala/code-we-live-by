import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import LawTextViewer from './LawTextViewer';

describe('LawTextViewer', () => {
  it('renders a line number for each line', () => {
    // Three distinct non-empty lines separated by newlines
    const content = 'SEC. 1.\nSEC. 2.\nSEC. 3.';
    render(<LawTextViewer content={content} />);
    expect(screen.getByText('SEC. 1.')).toBeInTheDocument();
    expect(screen.getByText('SEC. 2.')).toBeInTheDocument();
    expect(screen.getByText('SEC. 3.')).toBeInTheDocument();
    // Line numbers 1–3 should all be present
    const { container } = render(<LawTextViewer content={content} />);
    const lineNums = Array.from(
      container.querySelectorAll('.text-gray-400')
    ).map((el) => el.textContent?.trim());
    expect(lineNums).toContain('1');
    expect(lineNums).toContain('3');
  });

  it('normalizes leading tabs to 4-space indentation', () => {
    const content = 'top level\n\tindented once\n\t\tindented twice';
    const { container } = render(<LawTextViewer content={content} />);
    const spans = container.querySelectorAll('span.text-gray-800');
    const texts = Array.from(spans).map((s) => s.textContent);
    expect(texts).toContain('top level');
    expect(texts).toContain('    indented once');
    expect(texts).toContain('        indented twice');
  });

  it('strips HTML wrapper tags', () => {
    render(
      <LawTextViewer content="<html><body><pre>content here</pre></body></html>" />
    );
    expect(screen.getByText('content here')).toBeInTheDocument();
  });

  it('removes GPO end-of-document marker', () => {
    const { container } = render(<LawTextViewer content="text<all>" />);
    expect(container.textContent).not.toContain('<all>');
    expect(container.textContent).toContain('text');
  });
});
