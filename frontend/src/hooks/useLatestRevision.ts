import { useQuery } from '@tanstack/react-query';
import { fetchLatestRevisionForTitle } from '@/lib/api';

export function useLatestRevisionForTitle(titleNumber: number) {
  return useQuery({
    queryKey: ['latest-revision', 'title', titleNumber],
    queryFn: () => fetchLatestRevisionForTitle(titleNumber),
    staleTime: 5 * 60 * 1000,
  });
}
