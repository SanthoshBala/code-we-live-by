import { useState, useEffect } from 'react';
import Link from 'next/link';
import type { TitleSummary, TreeActivePath } from '@/lib/types';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import TreeIndicator from './TreeIndicator';
import ChapterGroupNode from './ChapterGroupNode';
import ChapterNode from './ChapterNode';

interface TitleNodeProps {
  title: TitleSummary;
  activePath?: TreeActivePath;
}

/** Expandable title row. Lazy-loads structure on first expand. */
export default function TitleNode({ title, activePath }: TitleNodeProps) {
  const [expanded, setExpanded] = useState(!!activePath);
  const { data: structure, isLoading } = useTitleStructure(
    title.title_number,
    expanded
  );

  useEffect(() => {
    if (activePath) setExpanded(true);
  }, [activePath]);

  const isActive =
    activePath?.titleNumber === title.title_number &&
    !activePath?.chapterNumber &&
    !activePath?.groupPath?.length;

  return (
    <div>
      <div
        className={`flex w-full items-center gap-1.5 rounded px-2 py-1 text-sm font-semibold text-gray-800 hover:bg-gray-100 ${isActive ? 'bg-primary-50' : ''}`}
      >
        <TreeIndicator
          expanded={expanded}
          onToggle={() => setExpanded((prev) => !prev)}
        />
        <Link
          href={`/titles/${title.title_number}`}
          className="min-w-0 truncate hover:text-primary-700"
        >
          {title.title_name}
        </Link>
        <span className="ml-auto shrink-0 text-xs font-normal text-gray-400">
          {title.section_count}
        </span>
      </div>
      {expanded && (
        <div className="ml-4 border-l border-gray-300 pl-2">
          <p className="px-2 py-0.5 font-mono text-xs text-gray-400">
            Title {title.title_number}
          </p>
          {isLoading && (
            <p className="px-2 py-0.5 text-xs text-gray-400">Loading...</p>
          )}
          {structure?.chapter_groups?.map((g) => (
            <ChapterGroupNode
              key={`${g.group_type}-${g.group_number}`}
              group={g}
              titleNumber={title.title_number}
              parentPath={`/titles/${title.title_number}`}
              activePath={activePath}
            />
          ))}
          {structure?.chapters.map((ch) => (
            <ChapterNode
              key={ch.chapter_number}
              chapter={ch}
              titleNumber={title.title_number}
              activePath={activePath}
            />
          ))}
        </div>
      )}
    </div>
  );
}
