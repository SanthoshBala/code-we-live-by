import type { HeadRevision } from './types';

/** Format a revision into a human-readable label like "Release Point 113-21 · Jul 18, 2013". */
export function formatRevisionLabel(
  revisionType: string,
  summary: string | null,
  effectiveDate: string
): string {
  const date = new Date(effectiveDate + 'T00:00:00');
  const formatted = date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  if (summary) {
    return `${summary} · ${formatted}`;
  }

  const typeLabel =
    revisionType === 'Release_Point' ? 'Release Point' : 'Public Law';
  return `${typeLabel} · ${formatted}`;
}

/** Build a label from a HeadRevision object. */
export function revisionLabel(revision: HeadRevision): string {
  return formatRevisionLabel(
    revision.revision_type,
    revision.summary,
    revision.effective_date
  );
}
