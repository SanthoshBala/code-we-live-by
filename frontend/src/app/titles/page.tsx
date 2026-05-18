import type { DirectoryItem } from '@/lib/types';
import DirectoryView from '@/components/directory/DirectoryView';
import { fetchTitlesServer } from '@/lib/api.server';

export const revalidate = 300;

/** All titles directory page (SSR with ISR). */
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
