import { useState, useEffect } from 'react';
import Link from 'next/link';
import type { ChapterGroupTree, TreeActivePath } from '@/lib/types';
import TreeIndicator from './TreeIndicator';
import ChapterNode from './ChapterNode';

interface ChapterGroupNodeProps {
  group: ChapterGroupTree;
  titleNumber: number;
  parentPath: string;
  activePath?: TreeActivePath;
}

function groupContainsActive(
  group: ChapterGroupTree,
  activePath?: TreeActivePath
): boolean {
  if (!activePath) return false;
  // Check if this group is on the active group path
  if (
    activePath.groupPath?.some(
      (gp) => gp.type === group.group_type && gp.number === group.group_number
    )
  ) {
    return true;
  }
  // Check chapters in this group
  for (const ch of group.chapters) {
    if (activePath.chapterNumber === ch.chapter_number) return true;
    if (activePath.sectionNumber) {
      if (
        ch.sections.some(
          (s) => s.section_number === activePath.sectionNumber
        ) ||
        ch.subchapters.some((sub) =>
          sub.sections.some(
            (s) => s.section_number === activePath.sectionNumber
          )
        )
      ) {
        return true;
      }
    }
  }
  // Recurse into child groups
  return group.child_groups.some((cg) => groupContainsActive(cg, activePath));
}

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

/** Expandable structural group node (subtitle, part, division) in the tree. */
export default function ChapterGroupNode({
  group,
  titleNumber,
  parentPath,
  activePath,
}: ChapterGroupNodeProps) {
  const groupHref = `${parentPath}/${group.group_type}/${group.group_number}`;
  const [expanded, setExpanded] = useState(
    groupContainsActive(group, activePath)
  );

  useEffect(() => {
    if (groupContainsActive(group, activePath)) setExpanded(true);
  }, [group, activePath]);

  return (
    <div>
      <div className="flex w-full items-center gap-1 rounded px-2 py-0.5 text-xs font-medium text-gray-700 hover:bg-gray-100">
        <TreeIndicator
          expanded={expanded}
          onToggle={() => setExpanded((prev) => !prev)}
        />
        <Link
          href={groupHref}
          className="min-w-0 truncate text-left hover:text-primary-700"
        >
          {group.group_name}
        </Link>
      </div>
      {expanded && (
        <div className="ml-4 border-l border-gray-300 pl-2">
          <p className="px-2 py-0.5 font-mono text-xs text-gray-400">
            {capitalizeGroupType(group.group_type)} {group.group_number}
          </p>
          {group.child_groups.map((cg) => (
            <ChapterGroupNode
              key={`${cg.group_type}-${cg.group_number}`}
              group={cg}
              titleNumber={titleNumber}
              parentPath={groupHref}
              activePath={activePath}
            />
          ))}
          {group.chapters.map((ch) => (
            <ChapterNode
              key={ch.chapter_number}
              chapter={ch}
              titleNumber={titleNumber}
              activePath={activePath}
            />
          ))}
        </div>
      )}
    </div>
  );
}
