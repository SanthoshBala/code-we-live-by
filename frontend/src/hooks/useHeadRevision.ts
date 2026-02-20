import { useQuery } from '@tanstack/react-query';
import { fetchHeadRevision } from '@/lib/api';

export function useHeadRevision() {
  return useQuery({
    queryKey: ['head-revision'],
    queryFn: fetchHeadRevision,
    staleTime: 5 * 60 * 1000,
  });
}
