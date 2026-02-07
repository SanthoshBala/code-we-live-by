import { useState } from 'react';
import type { ChapterTree } from '@/lib/types';
import TreeIndicator from './TreeIndicator';
import SubchapterNode from './SubchapterNode';
import SectionNode from './SectionNode';

interface ChapterNodeProps {
  chapter: ChapterTree;
  titleNumber: number;
  compact?: boolean;
  activeSectionNumber?: string;
}

function chapterContainsSection(
  chapter: ChapterTree,
  sectionNumber: string
): boolean {
  return (
    chapter.sections.some((s) => s.section_number === sectionNumber) ||
    chapter.subchapters.some((sub) =>
      sub.sections.some((s) => s.section_number === sectionNumber)
    )
  );
}

/** Expandable chapter row in the tree. */
export default function ChapterNode({
  chapter,
  titleNumber,
  compact,
  activeSectionNumber,
}: ChapterNodeProps) {
  const [expanded, setExpanded] = useState(
    !!activeSectionNumber &&
      chapterContainsSection(chapter, activeSectionNumber)
  );

  return (
    <div>
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className={`flex w-full items-center gap-1 rounded px-2 text-left font-medium text-gray-700 hover:bg-gray-100 ${compact ? 'py-0.5 text-xs' : 'py-1 text-sm'}`}
      >
        <TreeIndicator expanded={expanded} />
        <span className="truncate">
          Chapter {chapter.chapter_number} &mdash; {chapter.chapter_name}
        </span>
      </button>
      {expanded && (
        <div className="ml-4 border-l border-gray-300 pl-2">
          <p className="px-2 py-0.5 font-mono text-xs text-gray-400">
            USC / Title {titleNumber} / Ch. {chapter.chapter_number}
          </p>
          {chapter.subchapters.map((sub) => (
            <SubchapterNode
              key={sub.subchapter_number}
              subchapter={sub}
              titleNumber={titleNumber}
              chapterNumber={chapter.chapter_number}
              compact={compact}
              activeSectionNumber={activeSectionNumber}
            />
          ))}
          {chapter.sections.map((section) => (
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
