import { useQuery } from '@tanstack/react-query';
import { fetchSection } from '@/lib/api';

/** Fetches the full section detail view, optionally at a specific revision. */
export function useSection(
  titleNumber: number,
  sectionNumber: string,
  revision?: number
) {
  return useQuery({
    queryKey: ['section', titleNumber, sectionNumber, revision ?? 'head'],
    queryFn: () => fetchSection(titleNumber, sectionNumber, revision),
  });
}
