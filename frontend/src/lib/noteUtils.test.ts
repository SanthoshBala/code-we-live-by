import { describe, it, expect } from 'vitest';
import {
  slugify,
  buildCrossRefLookup,
  getDirectionalUrl,
  findNoteLinks,
} from './noteUtils';
import type { SectionNote } from './types';

describe('slugify', () => {
  it('lowercases and replaces spaces with dashes', () => {
    expect(slugify('Effective and Termination Date')).toBe(
      'effective-and-termination-date'
    );
  });

  it('removes non-word characters', () => {
    expect(slugify('References in Text')).toBe('references-in-text');
  });

  it('collapses multiple dashes', () => {
    expect(slugify('Short  Title')).toBe('short-title');
  });

  it('handles a single word', () => {
    expect(slugify('Amendments')).toBe('amendments');
  });
});

const basePath = '/sections/50/541';

const allNotes: Pick<SectionNote, 'header' | 'category'>[] = [
  { header: 'References in Text', category: 'editorial' },
  { header: 'Codification', category: 'editorial' },
  { header: 'Effective and Termination Date', category: 'statutory' },
  { header: 'Short Title', category: 'statutory' },
];

describe('buildCrossRefLookup', () => {
  it('maps each header slug to its URL with anchor', () => {
    const lookup = buildCrossRefLookup(allNotes, basePath);
    expect(lookup.get('references-in-text')?.url).toBe(
      '/sections/50/541/EDITORIAL_NOTES#references-in-text'
    );
    expect(lookup.get('effective-and-termination-date')?.url).toBe(
      '/sections/50/541/STATUTORY_NOTES#effective-and-termination-date'
    );
  });

  it('stores the original header and category', () => {
    const lookup = buildCrossRefLookup(allNotes, basePath);
    const ref = lookup.get('short-title');
    expect(ref?.header).toBe('Short Title');
    expect(ref?.category).toBe('statutory');
  });

  it('returns an empty map for empty input', () => {
    expect(buildCrossRefLookup([], basePath).size).toBe(0);
  });
});

describe('getDirectionalUrl', () => {
  const available = new Set(['editorial', 'statutory']);

  it('returns statutory URL for "below" from editorial', () => {
    const url = getDirectionalUrl('below', 'editorial', available, basePath);
    expect(url).toBe('/sections/50/541/STATUTORY_NOTES');
  });

  it('returns null for "below" from statutory (nothing below)', () => {
    const url = getDirectionalUrl('below', 'statutory', available, basePath);
    expect(url).toBeNull();
  });

  it('returns editorial URL for "above" from statutory', () => {
    const url = getDirectionalUrl('above', 'statutory', available, basePath);
    expect(url).toBe('/sections/50/541/EDITORIAL_NOTES');
  });

  it('skips categories not in the available set', () => {
    const url = getDirectionalUrl(
      'below',
      'historical',
      new Set(['statutory']),
      basePath
    );
    expect(url).toBe('/sections/50/541/STATUTORY_NOTES');
  });

  it('returns null for unknown category', () => {
    const url = getDirectionalUrl('below', 'unknown', available, basePath);
    expect(url).toBeNull();
  });
});

describe('findNoteLinks', () => {
  const lookup = buildCrossRefLookup(allNotes, basePath);

  it('detects named note reference with direction', () => {
    const content =
      'See Effective and Termination Date note below.';
    const matches = findNoteLinks(content, lookup, 'editorial', basePath);
    expect(matches).toHaveLength(1);
    expect(matches[0].text).toBe('Effective and Termination Date note below');
    expect(matches[0].url).toBe(
      '/sections/50/541/STATUTORY_NOTES#effective-and-termination-date'
    );
  });

  it('detects named note reference without direction', () => {
    const content = 'See Effective and Termination Date note.';
    const matches = findNoteLinks(content, lookup, 'editorial', basePath);
    expect(matches).toHaveLength(1);
    expect(matches[0].text).toBe('Effective and Termination Date note');
  });

  it('detects bare directional reference "note below"', () => {
    const content = 'See note below.';
    const matches = findNoteLinks(content, lookup, 'editorial', basePath);
    expect(matches).toHaveLength(1);
    expect(matches[0].text).toBe('note below');
    expect(matches[0].url).toBe('/sections/50/541/STATUTORY_NOTES');
  });

  it('detects "note set out below" variant', () => {
    const content = 'see note set out below for details.';
    const matches = findNoteLinks(content, lookup, 'editorial', basePath);
    expect(matches).toHaveLength(1);
    expect(matches[0].text).toBe('note set out below');
    expect(matches[0].url).toBe('/sections/50/541/STATUTORY_NOTES');
  });

  it('does not link same-category notes', () => {
    // "References in Text" is also editorial — should not be linked from editorial
    const content = 'See References in Text note below.';
    const matches = findNoteLinks(content, lookup, 'editorial', basePath);
    // "note below" (bare directional) should still match
    expect(matches).toHaveLength(1);
    expect(matches[0].text).toBe('note below');
  });

  it('returns no matches when content has no cross-references', () => {
    const content = 'Pub. L. 91-452 amended this section.';
    const matches = findNoteLinks(content, lookup, 'editorial', basePath);
    expect(matches).toHaveLength(0);
  });

  it('returns empty for an empty crossRefs map', () => {
    const matches = findNoteLinks(
      'See note below.',
      new Map(),
      'editorial',
      basePath
    );
    expect(matches).toHaveLength(0);
  });

  it('does not double-match a named reference as also a bare directional', () => {
    const content = 'See Effective and Termination Date note below.';
    const matches = findNoteLinks(content, lookup, 'editorial', basePath);
    expect(matches).toHaveLength(1);
  });
});
