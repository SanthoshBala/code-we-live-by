'use client';

import { useTitles } from '@/hooks/useTitles';
import { TreeDisplayProvider } from '@/contexts/TreeDisplayContext';
import TitleNode from './TitleNode';
import TreeSettingsPanel from './TreeSettingsPanel';

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
    <TreeDisplayProvider>
      {!compact && <TreeSettingsPanel />}
      <nav aria-label="US Code titles">
        <div className="space-y-0.5">
          {titles.map((title) => (
            <TitleNode
              key={title.title_number}
              title={title}
              compact={compact}
            />
          ))}
        </div>
      </nav>
    </TreeDisplayProvider>
  );
}
