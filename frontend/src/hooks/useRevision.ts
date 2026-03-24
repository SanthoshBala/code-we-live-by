'use client';

import { useSearchParams } from 'next/navigation';
import { useCallback } from 'react';

/**
 * Reads the `?rev=` query parameter from the URL.
 *
 * Returns the revision ID as a number (or undefined for HEAD),
 * plus a helper to append `?rev=` to any href.
 */
export function useRevision() {
  const searchParams = useSearchParams();
  const revParam = searchParams.get('rev');
  const revision = revParam ? Number(revParam) : undefined;

  /** Append ?rev=N to an href if a revision is active. */
  const withRev = useCallback(
    (href: string): string => {
      if (revision === undefined) return href;
      const separator = href.includes('?') ? '&' : '?';
      return `${href}${separator}rev=${revision}`;
    },
    [revision]
  );

  return { revision, withRev };
}
