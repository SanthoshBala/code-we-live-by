'use client';

import { useTitles } from '@/hooks/useTitles';
import TitleNode from './TitleNode';

interface TitleListProps {
  compact?: boolean;
}

/** Root tree component. Fetches titles eagerly and renders TitleNodes. */
export default function TitleList({ compact }: TitleListProps) {
  const { data: titles, isLoading, error } = useTitles();

  if (isLoading) {
    return (
      <p className={`text-gray-400 ${compact ? 'text-xs' : 'text-sm'}`}>
        Loading titles...
      </p>
    );
  }

  if (error) {
    return (
      <p className={`text-red-500 ${compact ? 'text-xs' : 'text-sm'}`}>
        Failed to load titles.
      </p>
    );
  }

  if (!titles || titles.length === 0) {
    return (
      <p className={`text-gray-400 ${compact ? 'text-xs' : 'text-sm'}`}>
        No titles found.
      </p>
    );
  }

  return (
    <nav aria-label="US Code titles">
      {!compact && (
        <div className="mb-1 flex items-center border-b border-gray-200 px-2 pb-1 text-xs font-semibold text-gray-500">
          <span className="flex-1">Name</span>
          <span className="w-28 shrink-0 text-right">Last amended by</span>
          <span className="w-20 shrink-0 text-right">Date amended</span>
        </div>
      )}
      <div className="space-y-0.5">
        {titles.map((title) => (
          <TitleNode key={title.title_number} title={title} compact={compact} />
        ))}
      </div>
    </nav>
  );
}
