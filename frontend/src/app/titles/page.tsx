'use client';

import { useTitles } from '@/hooks/useTitles';
import type { DirectoryItem } from '@/lib/types';
import DirectoryView from '@/components/directory/DirectoryView';

/** All titles directory page. */
export default function TitlesPage() {
  const { data: titles, isLoading, error } = useTitles();

  if (isLoading) {
    return <p className="text-gray-500">Loading titles...</p>;
  }

  if (error || !titles) {
    return <p className="text-red-600">Failed to load titles.</p>;
  }

  const items: DirectoryItem[] = titles.map((t) => ({
    id: `Title ${t.title_number}`,
    name: t.title_name,
    href: `/titles/${t.title_number}`,
    kind: 'folder' as const,
    sectionCount: t.section_count,
  }));

  return <DirectoryView title="Browse the US Code" items={items} />;
}
