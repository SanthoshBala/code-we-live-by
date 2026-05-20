import { describe, it, expect } from 'vitest';
import { stripHtml } from './LawTextViewer';

describe('stripHtml', () => {
  it('normalizes leading tabs to 4-space indentation', () => {
    const raw = '\tSEC. 1.\n\t\t  This Act may be cited as the "Test Act".';
    const result = stripHtml(raw);
    expect(result).toBe(
      '    SEC. 1.\n          This Act may be cited as the "Test Act".'
    );
  });

  it('leaves non-leading tabs unchanged', () => {
    const raw = 'word\tword';
    const result = stripHtml(raw);
    expect(result).toBe('word\tword');
  });

  it('strips HTML wrapper tags', () => {
    const raw = '<html><body><pre>text</pre></body></html>';
    expect(stripHtml(raw)).toBe('text');
  });

  it('removes GPO end-of-document marker', () => {
    const raw = 'text\n<all>';
    expect(stripHtml(raw)).toBe('text');
  });

  it('trims leading and trailing blank lines', () => {
    const raw = '\n\ntext\n\n';
    expect(stripHtml(raw)).toBe('text');
  });
});
