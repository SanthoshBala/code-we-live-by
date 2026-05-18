import { fetchLawsServer } from '@/lib/api.server';
import LawsTable from './LawsTable';

export const revalidate = 300;

/** Public laws list page (SSR with ISR). Sorting stays client-side in LawsTable. */
export default async function LawsPage() {
  const laws = await fetchLawsServer();
  return <LawsTable laws={laws} />;
}
