import { useState } from 'react';
import type { SubchapterTree } from '@/lib/types';
import TreeIndicator from './TreeIndicator';
import SectionNode from './SectionNode';

interface SubchapterNodeProps {
  subchapter: SubchapterTree;
  titleNumber: number;
  chapterNumber: string;
  compact?: boolean;
  activeSectionNumber?: string;
}

/** Expandable subchapter row in the tree. */
export default function SubchapterNode({
  subchapter,
  titleNumber,
  chapterNumber,
  compact,
  activeSectionNumber,
}: SubchapterNodeProps) {
  const [expanded, setExpanded] = useState(
    !!activeSectionNumber &&
      subchapter.sections.some((s) => s.section_number === activeSectionNumber)
  );

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
        <div className="ml-4 border-l border-gray-300 pl-2">
          <p className="px-2 py-0.5 font-mono text-xs text-gray-400">
            USC / Title {titleNumber} / Ch. {chapterNumber} / Subch.{' '}
            {subchapter.subchapter_number}
          </p>
          {subchapter.sections.map((section) => (
            <SectionNode
              key={section.section_number}
              section={section}
              titleNumber={titleNumber}
              compact={compact}
              defaultExpanded={section.section_number === activeSectionNumber}
            />
          ))}
        </div>
      )}
    </div>
  );
}
