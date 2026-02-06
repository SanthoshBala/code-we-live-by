import { useState } from 'react';
import type { TitleSummary } from '@/lib/types';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import TreeIndicator from './TreeIndicator';
import ChapterNode from './ChapterNode';

interface TitleNodeProps {
  title: TitleSummary;
  compact?: boolean;
}

/** Expandable title row. Lazy-loads structure on first expand. */
export default function TitleNode({ title, compact }: TitleNodeProps) {
  const [expanded, setExpanded] = useState(false);
  const { data: structure, isLoading } = useTitleStructure(
    title.title_number,
    expanded
  );

  return (
    <div>
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className={`flex w-full items-center gap-1.5 rounded px-2 text-left font-semibold text-gray-800 hover:bg-gray-100 ${compact ? 'py-1 text-sm' : 'py-1.5 text-base'}`}
      >
        <TreeIndicator expanded={expanded} />
        <span className="truncate">
          Title {title.title_number} &mdash; {title.title_name}
        </span>
        <span
          className={`ml-auto shrink-0 font-normal text-gray-400 ${compact ? 'text-xs' : 'text-sm'}`}
        >
          {title.section_count}
        </span>
      </button>
      {expanded && (
        <div className="ml-4 border-l border-gray-300 pl-2">
          <p className="px-2 py-0.5 font-mono text-xs text-gray-400">
            USC / Title {title.title_number}
          </p>
          {isLoading && (
            <p
              className={`px-2 text-gray-400 ${compact ? 'py-0.5 text-xs' : 'py-1 text-sm'}`}
            >
              Loading...
            </p>
          )}
          {structure?.chapters.map((ch) => (
            <ChapterNode
              key={ch.chapter_number}
              chapter={ch}
              titleNumber={title.title_number}
              compact={compact}
            />
          ))}
        </div>
      )}
    </div>
  );
}
