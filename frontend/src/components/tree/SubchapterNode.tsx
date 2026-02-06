import { useState } from 'react';
import type { SubchapterTree } from '@/lib/types';
import { useTreeDisplay } from '@/contexts/TreeDisplayContext';
import TreeIndicator from './TreeIndicator';
import SectionLeaf from './SectionLeaf';

interface SubchapterNodeProps {
  subchapter: SubchapterTree;
  titleNumber: number;
  chapterNumber: string;
  compact?: boolean;
}

/** Expandable subchapter row in the tree. */
export default function SubchapterNode({
  subchapter,
  titleNumber,
  chapterNumber,
  compact,
}: SubchapterNodeProps) {
  const [expanded, setExpanded] = useState(false);
  const { settings } = useTreeDisplay();

  return (
    <div>
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className={`flex w-full items-center gap-1 rounded px-2 text-left text-gray-600 hover:bg-gray-100 ${compact ? 'py-0.5 text-xs' : 'py-1 text-sm'}`}
      >
        <TreeIndicator expanded={expanded} />
        <span className="truncate">
          Subchapter {subchapter.subchapter_number} &mdash;{' '}
          {subchapter.subchapter_name}
        </span>
      </button>
      {expanded && (
        <div
          className={`ml-4 ${settings.showTreeLines ? 'border-l border-gray-300 pl-2' : ''}`}
        >
          {settings.showBreadcrumb && (
            <p className="px-2 py-0.5 font-mono text-xs text-gray-400">
              USC / Title {titleNumber} / Ch. {chapterNumber} / Subch.{' '}
              {subchapter.subchapter_number}
            </p>
          )}
          {subchapter.sections.map((section) => (
            <SectionLeaf
              key={section.section_number}
              section={section}
              titleNumber={titleNumber}
              compact={compact}
            />
          ))}
        </div>
      )}
    </div>
  );
}
