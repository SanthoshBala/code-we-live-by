import { useState, useEffect } from 'react';
import Link from 'next/link';
import type { ChapterTree, TreeActivePath } from '@/lib/types';
import TreeIndicator from './TreeIndicator';
import SubchapterNode from './SubchapterNode';
import SectionNode from './SectionNode';

interface ChapterNodeProps {
  chapter: ChapterTree;
  titleNumber: number;
  activePath?: TreeActivePath;
}

function chapterContainsActive(
  chapter: ChapterTree,
  activePath?: TreeActivePath
): boolean {
  if (!activePath) return false;
  if (activePath.chapterNumber) {
    return chapter.chapter_number === activePath.chapterNumber;
  }
  if (activePath.sectionNumber) {
    return (
      chapter.sections.some(
        (s) => s.section_number === activePath.sectionNumber
      ) ||
      chapter.subchapters.some((sub) =>
        sub.sections.some((s) => s.section_number === activePath.sectionNumber)
      )
    );
  }
  return false;
}

/** Expandable chapter row in the tree. */
export default function ChapterNode({
  chapter,
  titleNumber,
  activePath,
}: ChapterNodeProps) {
  const [expanded, setExpanded] = useState(
    chapterContainsActive(chapter, activePath)
  );

  useEffect(() => {
    if (chapterContainsActive(chapter, activePath)) setExpanded(true);
  }, [chapter, activePath]);

  const isActive =
    activePath?.chapterNumber === chapter.chapter_number &&
    !activePath?.subchapterNumber &&
    !activePath?.sectionNumber;

  return (
    <div>
      <div
        className={`flex w-full items-center gap-1 rounded px-2 py-0.5 text-xs font-medium text-gray-700 hover:bg-gray-100 ${isActive ? 'bg-primary-50' : ''}`}
      >
        <TreeIndicator
          expanded={expanded}
          onToggle={() => setExpanded((prev) => !prev)}
        />
        <Link
          href={`/titles/${titleNumber}/chapters/${chapter.chapter_number}`}
          className="min-w-0 truncate hover:text-primary-700"
        >
          {chapter.chapter_name}
        </Link>
      </div>
      {expanded && (
        <div className="ml-4 border-l border-gray-300 pl-2">
          <p className="px-2 py-0.5 font-mono text-xs text-gray-400">
            Chapter {chapter.chapter_number}
          </p>
          {chapter.subchapters.map((sub) => (
            <SubchapterNode
              key={sub.subchapter_number}
              subchapter={sub}
              titleNumber={titleNumber}
              chapterNumber={chapter.chapter_number}
              activePath={activePath}
            />
          ))}
          {chapter.sections.map((section) => (
            <SectionNode
              key={section.section_number}
              section={section}
              titleNumber={titleNumber}
              isActive={activePath?.sectionNumber === section.section_number}
            />
          ))}
        </div>
      )}
    </div>
  );
}
