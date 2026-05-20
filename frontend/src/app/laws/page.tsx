import { fetchLawsServer } from '@/lib/api.server';
import LawsTable from './LawsTable';

// No backend available at build time, so skip static prerendering.
// Data is still fetched server-side on every request (no client waterfall).
export const dynamic = 'force-dynamic';

const PAGE_SIZE = 50;

/** Public laws list page (SSR). Sorting stays client-side per page in LawsTable. */
export default async function LawsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? 1));
  const offset = (page - 1) * PAGE_SIZE;
  const data = await fetchLawsServer(PAGE_SIZE, offset);
  return (
    <LawsTable
      laws={data.items}
      total={data.total}
      page={page}
      limit={PAGE_SIZE}
    />
  );
}
