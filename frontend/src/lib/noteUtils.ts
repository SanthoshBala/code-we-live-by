import type { SectionNote } from '@/lib/types';

const CATEGORY_ORDER = ['historical', 'editorial', 'statutory'] as const;
type NoteCategory = (typeof CATEGORY_ORDER)[number];

const CATEGORY_TO_FILE: Record<NoteCategory, string> = {
  historical: 'HISTORICAL_NOTES',
  editorial: 'EDITORIAL_NOTES',
  statutory: 'STATUTORY_NOTES',
};

/** Convert a note header to a URL-safe anchor slug. */
export function slugify(header: string): string {
  return header
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim();
}

export interface CrossRef {
  url: string;
  header: string;
  category: NoteCategory;
}

/** Maps slugified note header → cross-ref target. */
export type CrossRefLookup = Map<string, CrossRef>;

/** Build a lookup of all note headers → their URL (including anchor). */
export function buildCrossRefLookup(
  allNotes: Pick<SectionNote, 'header' | 'category'>[],
  basePath: string
): CrossRefLookup {
  const lookup = new Map<string, CrossRef>();
  for (const note of allNotes) {
    const category = note.category as NoteCategory;
    const file = CATEGORY_TO_FILE[category];
    if (!file) continue;
    const anchor = slugify(note.header);
    lookup.set(anchor, {
      url: `${basePath}/${file}#${anchor}`,
      header: note.header,
      category,
    });
  }
  return lookup;
}

/** Return the URL for the next/previous note category (for bare "note below/above"). */
export function getDirectionalUrl(
  direction: 'below' | 'above',
  currentCategory: string,
  availableCategories: Set<string>,
  basePath: string
): string | null {
  const idx = CATEGORY_ORDER.indexOf(currentCategory as NoteCategory);
  if (idx === -1) return null;
  if (direction === 'below') {
    for (let i = idx + 1; i < CATEGORY_ORDER.length; i++) {
      const cat = CATEGORY_ORDER[i];
      if (availableCategories.has(cat)) {
        return `${basePath}/${CATEGORY_TO_FILE[cat]}`;
      }
    }
  } else {
    for (let i = idx - 1; i >= 0; i--) {
      const cat = CATEGORY_ORDER[i];
      if (availableCategories.has(cat)) {
        return `${basePath}/${CATEGORY_TO_FILE[cat]}`;
      }
    }
  }
  return null;
}

interface MatchSegment {
  start: number;
  end: number;
  url: string;
  text: string;
}

/**
 * Parse a content string and return segments that should be rendered as links.
 * Named note references (e.g. "Effective and Termination Date note below") take
 * priority over bare directional references ("note below").
 */
export function findNoteLinks(
  content: string,
  crossRefs: CrossRefLookup,
  currentCategory: string,
  basePath: string
): MatchSegment[] {
  const matches: MatchSegment[] = [];

  // 1. Named note references: "<header> note[ below|above|set out below|set out above]"
  for (const ref of crossRefs.values()) {
    if (ref.category === currentCategory) continue;
    const escaped = ref.header.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(
      `${escaped}\\s+note(?:\\s+(?:set\\s+out\\s+)?(?:below|above))?`,
      'gi'
    );
    let m: RegExpExecArray | null;
    while ((m = pattern.exec(content)) !== null) {
      matches.push({ start: m.index, end: m.index + m[0].length, url: ref.url, text: m[0] });
    }
  }

  // 2. Bare directional references: "note [set out] below|above"
  //    Only if not already covered by a named match.
  const availableCategories = new Set(
    Array.from(crossRefs.values()).map((r) => r.category as string)
  );
  const dirPattern = /\bnote(?:\s+set\s+out)?\s+(below|above)\b/gi;
  let dm: RegExpExecArray | null;
  while ((dm = dirPattern.exec(content)) !== null) {
    const start = dm.index;
    const end = dm.index + dm[0].length;
    const alreadyCovered = matches.some((m) => start >= m.start && end <= m.end);
    if (alreadyCovered) continue;
    const direction = dm[1].toLowerCase() as 'below' | 'above';
    const url = getDirectionalUrl(direction, currentCategory, availableCategories, basePath);
    if (url) {
      matches.push({ start, end, url, text: dm[0] });
    }
  }

  if (matches.length === 0) return [];

  // Sort by start position, then remove overlaps (keep first occurrence).
  matches.sort((a, b) => a.start - b.start || b.end - a.end);
  const result: MatchSegment[] = [matches[0]];
  for (let i = 1; i < matches.length; i++) {
    if (matches[i].start >= result[result.length - 1].end) {
      result.push(matches[i]);
    }
  }
  return result;
}
