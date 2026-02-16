import { useState, useEffect } from 'react';
import Link from 'next/link';
import type { SectionGroupTree, TreeActivePath } from '@/lib/types';
import { detectStatus } from '@/lib/statusStyles';
import TreeIndicator from './TreeIndicator';
import SectionNode from './SectionNode';

interface GroupNodeProps {
  group: SectionGroupTree;
  titleNumber: number;
  parentPath: string;
  activePath?: TreeActivePath;
}

function groupContainsActive(
  group: SectionGroupTree,
  activePath?: TreeActivePath
): boolean {
  if (!activePath) return false;
  // Check if this group is on the active group path
  if (
    activePath.groupPath?.some(
      (gp) => gp.type === group.group_type && gp.number === group.number
    )
  ) {
    return true;
  }
  // Check sections in this group
  if (
    activePath.sectionNumber &&
    group.sections.some((s) => s.section_number === activePath.sectionNumber)
  ) {
    return true;
  }
  // Recurse into child groups
  return group.children.some((child) => groupContainsActive(child, activePath));
}

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

/** Expandable structural group node (chapter, subchapter, subtitle, part, division, etc.) in the tree. */
export default function GroupNode({
  group,
  titleNumber,
  parentPath,
  activePath,
}: GroupNodeProps) {
  const groupHref = `${parentPath}/${group.group_type}/${group.number}`;
  const [expanded, setExpanded] = useState(
    groupContainsActive(group, activePath)
  );

  useEffect(() => {
    if (groupContainsActive(group, activePath)) setExpanded(true);
  }, [group, activePath]);

  const status = detectStatus(group.name);

  const isActive =
    activePath?.groupPath?.length &&
    activePath.groupPath[activePath.groupPath.length - 1].type ===
      group.group_type &&
    activePath.groupPath[activePath.groupPath.length - 1].number ===
      group.number &&
    !activePath?.sectionNumber;

  return (
    <div>
      <div
        className={`flex w-full items-center gap-1 rounded px-2 py-0.5 text-xs font-medium text-gray-700 hover:bg-gray-100 ${isActive ? 'bg-primary-50' : ''}`}
      >
        <TreeIndicator
          expanded={expanded}
          onToggle={() => setExpanded((prev) => !prev)}
          status={status}
        />
        <Link
          href={groupHref}
          className="min-w-0 truncate text-left hover:text-primary-700"
        >
          {group.name}
        </Link>
      </div>
      {expanded && (
        <div className="ml-4 border-l border-gray-300 pl-2">
          <p className="py-0.5 pl-3 pr-2 font-mono text-xs text-gray-400">
            {capitalizeGroupType(group.group_type)} {group.number}
          </p>
          {group.children.map((child) => (
            <GroupNode
              key={`${child.group_type}-${child.number}`}
              group={child}
              titleNumber={titleNumber}
              parentPath={groupHref}
              activePath={activePath}
            />
          ))}
          {group.sections.map((section) => (
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
