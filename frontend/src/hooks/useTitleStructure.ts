import { useQuery } from '@tanstack/react-query';
import { fetchTitleStructure } from '@/lib/api';

/**
 * Fetches the chapter/subchapter/section structure for a title.
 * Only fires when `enabled` is true (lazy loading on expand).
 * Optionally scoped to a specific revision.
 */
export function useTitleStructure(
  titleNumber: number,
  enabled: boolean,
  revision?: number
) {
  return useQuery({
    queryKey: ['titleStructure', titleNumber, revision ?? 'head'],
    queryFn: () => fetchTitleStructure(titleNumber, revision),
    enabled,
  });
}
