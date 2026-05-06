import { useQuery } from '@tanstack/react-query';
import { fetchLatestRevisionForTitle, fetchRevision } from '@/lib/api';

export function useLatestRevisionForTitle(titleNumber: number) {
  return useQuery({
    queryKey: ['latest-revision', 'title', titleNumber],
    queryFn: () => fetchLatestRevisionForTitle(titleNumber),
    staleTime: 5 * 60 * 1000,
  });
}

export function useRevisionById(revisionId: number | undefined) {
  return useQuery({
    queryKey: ['revision', revisionId],
    queryFn: () => fetchRevision(revisionId!),
    enabled: revisionId !== undefined,
    staleTime: Infinity,
  });
}
