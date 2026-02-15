'use client';

import Link from 'next/link';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import type { SectionGroupTree, TitleStructure } from '@/lib/types';

interface GroupAncestor {
  type: string;
  number: string;
}

interface SectionPath {
  groupAncestors: GroupAncestor[];
}

function findSectionInGroups(
  groups: SectionGroupTree[],
  sectionNumber: string,
  ancestors: GroupAncestor[] = []
): SectionPath | null {
  for (const g of groups) {
    const path = [...ancestors, { type: g.group_type, number: g.number }];
    const direct = g.sections.find((s) => s.section_number === sectionNumber);
    if (direct) {
      return { groupAncestors: path };
    }
    const nested = findSectionInGroups(g.children, sectionNumber, path);
    if (nested) return nested;
  }
  return null;
}

function findSection(
  structure: TitleStructure,
  sectionNumber: string
): SectionPath | null {
  const direct = (structure.sections ?? []).find(
    (s) => s.section_number === sectionNumber
  );
  if (direct) {
    return { groupAncestors: [] };
  }
  return findSectionInGroups(structure.children ?? [], sectionNumber);
}

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

interface SectionBreadcrumbProps {
  titleNumber: number;
  sectionNumber: string;
}

/** Renders a breadcrumb path for a USC section (e.g. "Title 50 / Chapter 36 / § 1881a"). */
export default function SectionBreadcrumb({
  titleNumber,
  sectionNumber,
}: SectionBreadcrumbProps) {
  const { data: structure } = useTitleStructure(titleNumber, true);

  if (!structure) {
    return (
      <span className="text-sm font-semibold text-gray-900">
        {titleNumber} U.S.C. &sect;&thinsp;{sectionNumber}
      </span>
    );
  }

  const path = findSection(structure, sectionNumber);

  const segments: { label: string; href?: string }[] = [
    { label: `Title ${titleNumber}`, href: `/titles/${titleNumber}` },
  ];

  if (path) {
    let pathSoFar = `/titles/${titleNumber}`;
    for (const ancestor of path.groupAncestors) {
      pathSoFar += `/${ancestor.type}/${ancestor.number}`;
      segments.push({
        label: `${capitalizeGroupType(ancestor.type)} ${ancestor.number}`,
        href: pathSoFar,
      });
    }
  }

  segments.push({ label: `\u00A7\u2009${sectionNumber}` });

  return (
    <nav aria-label="Section breadcrumb" className="text-sm text-gray-900">
      {segments.map((seg, i) => (
        <span key={i}>
          {i > 0 && <span className="mx-1 text-gray-400">/</span>}
          {seg.href ? (
            <Link
              href={seg.href}
              className="font-medium hover:text-primary-700"
            >
              {seg.label}
            </Link>
          ) : (
            <span className="font-semibold">{seg.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
