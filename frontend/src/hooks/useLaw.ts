import { useQuery } from '@tanstack/react-query';
import {
  fetchLaws,
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

/** Fetches raw HTM/XML text for a single law. */
export function useLawText(congress: number, lawNumber: string) {
  return useQuery({
    queryKey: ['lawText', congress, lawNumber],
    queryFn: () => fetchLawText(congress, lawNumber),
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
