import { useQuery } from '@tanstack/react-query';
import { fetchTitleStructure } from '@/lib/api';

/**
 * Fetches the chapter/subchapter/section structure for a title.
 * Only fires when `enabled` is true (lazy loading on expand).
 */
export function useTitleStructure(titleNumber: number, enabled: boolean) {
  return useQuery({
    queryKey: ['titleStructure', titleNumber],
    queryFn: () => fetchTitleStructure(titleNumber),
    enabled,
  });
}
