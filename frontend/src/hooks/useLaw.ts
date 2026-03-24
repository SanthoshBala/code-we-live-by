import { useQuery } from '@tanstack/react-query';
import {
  fetchLaws,
  fetchLawMeta,
  fetchLawText,
  fetchLawAmendments,
  fetchLawDiffs,
} from '@/lib/api';

/** Fetches all public law summaries. */
export function useLaws() {
  return useQuery({
    queryKey: ['laws'],
    queryFn: () => fetchLaws(),
  });
}

/** Fetches law metadata only (titles, dates — no HTM/XML content). */
export function useLawMeta(congress: number, lawNumber: string) {
  return useQuery({
    queryKey: ['lawMeta', congress, lawNumber],
    queryFn: () => fetchLawMeta(congress, lawNumber),
  });
}

/** Fetches law text in a specific format. Only fires when enabled. */
export function useLawText(
  congress: number,
  lawNumber: string,
  format: 'htm' | 'xml',
  enabled: boolean = true
) {
  return useQuery({
    queryKey: ['lawText', congress, lawNumber, format],
    queryFn: () => fetchLawText(congress, lawNumber, format),
    enabled,
  });
}

/** Fetches parsed amendments for a single law (live parse). */
export function useLawAmendments(
  congress: number,
  lawNumber: string,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: ['lawAmendments', congress, lawNumber],
    queryFn: () => fetchLawAmendments(congress, lawNumber),
    enabled,
  });
}

/** Fetches per-section unified diffs for a single law. */
export function useLawDiffs(
  congress: number,
  lawNumber: string,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: ['lawDiffs', congress, lawNumber],
    queryFn: () => fetchLawDiffs(congress, lawNumber),
    enabled,
  });
}
