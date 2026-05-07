import type { ReactNode } from 'react';
import Link from 'next/link';
import type { NoteReference } from '@/lib/types';

interface Match {
  index: number;
  length: number;
  ref: NoteReference;
}

/** Build an internal route for a reference, or null if no route exists. */
function refToHref(ref: NoteReference): string | null {
  if (ref.ref_type === 'usc_section' && ref.usc_title && ref.usc_section) {
    return `/sections/${ref.usc_title}/${ref.usc_section}`;
  }
  if (ref.ref_type === 'public_law' && ref.congress && ref.law_number) {
    return `/laws/${ref.congress}/${ref.law_number}`;
  }
  return null;
}

/**
 * Replace reference display_text occurrences in `text` with clickable links.
 *
 * - USC section refs → internal Link to /sections/{title}/{section}
 * - Public law refs → internal Link to /laws/{congress}/{number}
 * - Act / statute refs → styled span (no internal route)
 * - `withRev` is applied to all internal hrefs to preserve ?rev= context.
 */
export function linkifyContent(
  text: string,
  references: NoteReference[],
  withRev: (href: string) => string
): ReactNode {
  if (references.length === 0) return text;

  // Sort by display_text length descending so longer matches take priority
  const sorted = [...references].sort(
    (a, b) => b.display_text.length - a.display_text.length
  );

  // Find all non-overlapping matches
  const matches: Match[] = [];
  for (const ref of sorted) {
    if (!ref.display_text) continue;
    let searchFrom = 0;
    while (searchFrom < text.length) {
      const idx = text.indexOf(ref.display_text, searchFrom);
      if (idx === -1) break;
      // Check no overlap with existing matches
      const end = idx + ref.display_text.length;
      const overlaps = matches.some(
        (m) => idx < m.index + m.length && end > m.index
      );
      if (!overlaps) {
        matches.push({ index: idx, length: ref.display_text.length, ref });
      }
      searchFrom = idx + 1;
    }
  }

  if (matches.length === 0) return text;

  // Sort matches by position
  matches.sort((a, b) => a.index - b.index);

  const linkClass = 'text-blue-600 hover:underline';
  const parts: ReactNode[] = [];
  let cursor = 0;

  for (const match of matches) {
    // Text before this match
    if (match.index > cursor) {
      parts.push(text.slice(cursor, match.index));
    }

    const display = text.slice(match.index, match.index + match.length);
    const href = refToHref(match.ref);

    if (href && match.ref.resolvable) {
      parts.push(
        <Link key={match.index} href={withRev(href)} className={linkClass}>
          {display}
        </Link>
      );
    } else {
      parts.push(
        <span
          key={match.index}
          className="text-red-600"
          title={match.ref.target_id}
        >
          {display}
        </span>
      );
    }

    cursor = match.index + match.length;
  }

  // Remaining text
  if (cursor < text.length) {
    parts.push(text.slice(cursor));
  }

  return <>{parts}</>;
}
