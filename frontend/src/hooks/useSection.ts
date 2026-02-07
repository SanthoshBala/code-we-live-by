import { useQuery } from '@tanstack/react-query';
import { fetchSection } from '@/lib/api';

/** Fetches the full section detail view. */
export function useSection(titleNumber: number, sectionNumber: string) {
  return useQuery({
    queryKey: ['section', titleNumber, sectionNumber],
    queryFn: () => fetchSection(titleNumber, sectionNumber),
  });
}
