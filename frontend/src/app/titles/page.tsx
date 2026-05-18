import type { DirectoryItem } from '@/lib/types';
import DirectoryView from '@/components/directory/DirectoryView';
import { fetchTitlesServer } from '@/lib/api.server';

// No backend available at build time, so skip static prerendering.
// Data is still fetched server-side on every request (no client waterfall).
export const dynamic = 'force-dynamic';

/** All titles directory page (SSR). */
export default async function TitlesPage() {
  const titles = await fetchTitlesServer();

  const items: DirectoryItem[] = titles.map((t) => ({
    id: `Title ${t.title_number}`,
    name: t.title_name,
    href: `/titles/${t.title_number}`,
    kind: 'folder' as const,
    sectionCount: t.section_count,
  }));

  return <DirectoryView title="Browse the US Code" items={items} />;
}
