import { useQuery } from '@tanstack/react-query';
import { fetchTitles } from '@/lib/api';

/** Fetches all US Code title summaries.
 *  Title list only changes when new revisions are ingested, so cache
 *  indefinitely within a session to avoid redundant refetches.
 */
export function useTitles() {
  return useQuery({
    queryKey: ['titles'],
    queryFn: fetchTitles,
    staleTime: Infinity,
  });
}
