'use client';

import { useTitles } from '@/hooks/useTitles';
import type { TreeActivePath } from '@/lib/types';
import TitleNode from './TitleNode';

interface TitleListProps {
  activePath?: TreeActivePath;
}

/** Root tree component. Fetches titles eagerly and renders TitleNodes. */
export default function TitleList({ activePath }: TitleListProps) {
  const { data: titles, isLoading, error } = useTitles();

  if (isLoading) {
    return <p className="text-xs text-gray-400">Loading titles...</p>;
  }

  if (error) {
    return <p className="text-xs text-red-500">Failed to load titles.</p>;
  }

  if (!titles || titles.length === 0) {
    return <p className="text-xs text-gray-400">No titles found.</p>;
  }

  return (
    <nav aria-label="US Code titles">
      <div className="space-y-0.5">
        {titles.map((title) => (
          <TitleNode
            key={title.title_number}
            title={title}
            activePath={
              title.title_number === activePath?.titleNumber
                ? activePath
                : undefined
            }
          />
        ))}
      </div>
    </nav>
  );
}
