'use client';

import { useState } from 'react';
import type { ParsedAmendment, SectionGroupTree } from '@/lib/types';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import TreeIndicator from '@/components/tree/TreeIndicator';
import FileIcon from '@/components/tree/icons/FileIcon';

interface AffectedSectionsTreeProps {
  amendments: ParsedAmendment[];
  activeSection: string | null;
  onSectionClick: (sectionKey: string) => void;
}

/** Extract unique {title, section} pairs from amendments. */
function extractAffectedSections(
  amendments: ParsedAmendment[]
): Map<number, Set<string>> {
  const titleSections = new Map<number, Set<string>>();
  for (const a of amendments) {
    if (!a.section_ref || a.section_ref.title == null) continue;
    const existing = titleSections.get(a.section_ref.title);
    if (existing) {
      existing.add(a.section_ref.section);
    } else {
      titleSections.set(a.section_ref.title, new Set([a.section_ref.section]));
    }
  }
  return titleSections;
}

/** Build the display key for a section (must match groupAmendmentsBySection in LawDiffViewer). */
function sectionDisplayKey(title: number, section: string): string {
  return `${title} U.S.C. § ${section}`;
}

/** Count amendments for a given section. */
function countAmendments(
  amendments: ParsedAmendment[],
  title: number,
  section: string
): number {
  return amendments.filter(
    (a) => a.section_ref?.title === title && a.section_ref?.section === section
  ).length;
}

/** Check if a group tree contains any of the affected sections. */
function groupContainsAffected(
  group: SectionGroupTree,
  affectedSections: Set<string>
): boolean {
  if (group.sections.some((s) => affectedSections.has(s.section_number))) {
    return true;
  }
  return group.children.some((child) =>
    groupContainsAffected(child, affectedSections)
  );
}

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

/** Renders a pruned group node matching GroupNode styling. */
function PrunedGroupNode({
  group,
  titleNumber,
  affectedSections,
  amendments,
  activeSection,
  onSectionClick,
}: {
  group: SectionGroupTree;
  titleNumber: number;
  affectedSections: Set<string>;
  amendments: ParsedAmendment[];
  activeSection: string | null;
  onSectionClick: (key: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);

  // Only render groups that contain affected sections
  if (!groupContainsAffected(group, affectedSections)) return null;

  const affectedChildren = group.children.filter((child) =>
    groupContainsAffected(child, affectedSections)
  );
  const affectedSectionNodes = group.sections.filter((s) =>
    affectedSections.has(s.section_number)
  );

  return (
    <div>
      <div className="flex w-full items-center gap-1 rounded px-2 py-0.5 text-xs font-medium text-gray-700 hover:bg-gray-100">
        <TreeIndicator
          expanded={expanded}
          onToggle={() => setExpanded((prev) => !prev)}
        />
        <span className="min-w-0 truncate">{group.name}</span>
      </div>
      {expanded && (
        <div className="ml-4 border-l border-gray-300 pl-2">
          <p className="px-2 py-0.5 font-mono text-xs text-gray-400">
            {capitalizeGroupType(group.group_type)} {group.number}
          </p>
          {affectedChildren.map((child) => (
            <PrunedGroupNode
              key={`${child.group_type}-${child.number}`}
              group={child}
              titleNumber={titleNumber}
              affectedSections={affectedSections}
              amendments={amendments}
              activeSection={activeSection}
              onSectionClick={onSectionClick}
            />
          ))}
          {affectedSectionNodes.map((section) => {
            const displayKey = sectionDisplayKey(
              titleNumber,
              section.section_number
            );
            const count = countAmendments(
              amendments,
              titleNumber,
              section.section_number
            );
            const isActive = activeSection === displayKey;
            return (
              <div key={section.section_number}>
                <div
                  className={`flex w-full items-center gap-1 rounded px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-100 ${isActive ? 'bg-primary-50' : ''}`}
                >
                  <TreeIndicator expanded={isActive} />
                  <button
                    onClick={() => onSectionClick(displayKey)}
                    className="min-w-0 truncate text-left hover:text-primary-700"
                  >
                    {section.heading}
                  </button>
                  <span className="ml-auto shrink-0 text-xs font-normal text-gray-400">
                    {count}
                  </span>
                </div>
                {isActive && (
                  <div className="ml-4 border-l border-gray-300 pl-2">
                    <p className="px-2 py-0.5 font-mono text-xs text-gray-400">
                      &sect;&thinsp;{section.section_number}
                    </p>
                    <button
                      onClick={() => onSectionClick(displayKey)}
                      className="flex items-center gap-1.5 rounded px-2 py-0.5 text-xs text-primary-700 hover:bg-primary-50"
                    >
                      <FileIcon />
                      <span className="truncate">{section.heading}</span>
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/** Tree for a single title — fetches structure and prunes to affected sections. */
function TitleTreeNode({
  titleNumber,
  affectedSections,
  amendments,
  activeSection,
  onSectionClick,
}: {
  titleNumber: number;
  affectedSections: Set<string>;
  amendments: ParsedAmendment[];
  activeSection: string | null;
  onSectionClick: (key: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const { data: structure, isLoading } = useTitleStructure(
    titleNumber,
    expanded
  );

  return (
    <div>
      <div className="flex w-full items-center gap-1.5 rounded px-2 py-1 text-sm font-semibold text-gray-800 hover:bg-gray-100">
        <TreeIndicator
          expanded={expanded}
          onToggle={() => setExpanded((prev) => !prev)}
        />
        <span className="min-w-0 truncate">Title {titleNumber}</span>
      </div>
      {expanded && (
        <div className="ml-4 border-l border-gray-300 pl-2">
          <p className="px-2 py-0.5 font-mono text-xs text-gray-400">
            Title {titleNumber}
          </p>
          {isLoading && (
            <p className="px-2 py-0.5 text-xs text-gray-400">Loading...</p>
          )}
          {structure?.children?.map((g) => (
            <PrunedGroupNode
              key={`${g.group_type}-${g.number}`}
              group={g}
              titleNumber={titleNumber}
              affectedSections={affectedSections}
              amendments={amendments}
              activeSection={activeSection}
              onSectionClick={onSectionClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** Sidebar tree of USC sections affected by a law, using the same hierarchy as the US Code viewer. */
export default function AffectedSectionsTree({
  amendments,
  activeSection,
  onSectionClick,
}: AffectedSectionsTreeProps) {
  const titleSections = extractAffectedSections(amendments);

  if (titleSections.size === 0) {
    return (
      <p className="px-2 py-2 text-xs text-gray-400">
        No section references found.
      </p>
    );
  }

  const sortedTitles = Array.from(titleSections.entries()).sort(
    ([a], [b]) => a - b
  );

  return (
    <nav aria-label="Affected USC sections">
      <div className="space-y-0.5">
        {sortedTitles.map(([titleNumber, sections]) => (
          <TitleTreeNode
            key={titleNumber}
            titleNumber={titleNumber}
            affectedSections={sections}
            amendments={amendments}
            activeSection={activeSection}
            onSectionClick={onSectionClick}
          />
        ))}
      </div>
    </nav>
  );
}
