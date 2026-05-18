import { fetchLawsServer } from '@/lib/api.server';
import LawsTable from './LawsTable';

// No backend available at build time, so skip static prerendering.
// Data is still fetched server-side on every request (no client waterfall).
export const dynamic = 'force-dynamic';

/** Public laws list page (SSR). Sorting stays client-side in LawsTable. */
export default async function LawsPage() {
  const laws = await fetchLawsServer();
  return <LawsTable laws={laws} />;
}
