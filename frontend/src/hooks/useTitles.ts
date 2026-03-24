import { useQuery } from '@tanstack/react-query';
import { fetchTitles } from '@/lib/api';

/** Fetches all US Code title summaries. */
export function useTitles() {
  return useQuery({
    queryKey: ['titles'],
    queryFn: fetchTitles,
  });
}
