import { useState, useEffect } from 'react';
import Link from 'next/link';
import type { SubchapterTree, TreeActivePath } from '@/lib/types';
import TreeIndicator from './TreeIndicator';
import SectionNode from './SectionNode';

interface SubchapterNodeProps {
  subchapter: SubchapterTree;
  titleNumber: number;
  chapterNumber: string;
  activePath?: TreeActivePath;
}

/** Expandable subchapter row in the tree. */
export default function SubchapterNode({
  subchapter,
  titleNumber,
  chapterNumber,
  activePath,
}: SubchapterNodeProps) {
  const isThisSub =
    (activePath?.subchapterNumber === subchapter.subchapter_number &&
      activePath?.chapterNumber === chapterNumber) ||
    (!activePath?.subchapterNumber &&
      !!activePath?.sectionNumber &&
      subchapter.sections.some(
        (s) => s.section_number === activePath.sectionNumber
      ));
  const [expanded, setExpanded] = useState(isThisSub);

  useEffect(() => {
    if (isThisSub) setExpanded(true);
  }, [isThisSub]);

  const isActive = isThisSub && !activePath?.sectionNumber;

  return (
    <div>
      <div
        className={`flex w-full items-center gap-1 rounded px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-100 ${isActive ? 'bg-primary-50' : ''}`}
      >
        <TreeIndicator
          expanded={expanded}
          onToggle={() => setExpanded((prev) => !prev)}
        />
        <Link
          href={`/titles/${titleNumber}/chapters/${chapterNumber}/subchapters/${subchapter.subchapter_number}`}
          className="min-w-0 truncate hover:text-primary-700"
        >
          {subchapter.subchapter_name}
        </Link>
      </div>
      {expanded && (
        <div className="ml-4 border-l border-gray-300 pl-2">
          <p className="px-2 py-0.5 font-mono text-xs text-gray-400">
            Subchapter {subchapter.subchapter_number}
          </p>
          {subchapter.sections.map((section) => (
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
