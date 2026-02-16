'use client';

import { useParams } from 'next/navigation';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import type {
  SectionGroupTree,
  DirectoryItem,
  SectionSummary,
  BreadcrumbSegment,
} from '@/lib/types';
import { detectStatus } from '@/lib/statusStyles';
import DirectoryView from '@/components/directory/DirectoryView';

function latestAmendment(sections: SectionSummary[]): {
  law: string | null;
  year: number | null;
} {
  let latest: { law: string | null; year: number | null } = {
    law: null,
    year: null,
  };
  for (const s of sections) {
    if (
      s.last_amendment_year &&
      (!latest.year || s.last_amendment_year > latest.year)
    ) {
      latest = {
        law: s.last_amendment_law ?? null,
        year: s.last_amendment_year,
      };
    }
  }
  return latest;
}

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function collectAllSections(group: SectionGroupTree): SectionSummary[] {
  const sections: SectionSummary[] = [...group.sections];
  for (const child of group.children) {
    sections.push(...collectAllSections(child));
  }
  return sections;
}

/**
 * Parse groupPath segments into alternating [type, number] pairs.
 * e.g. ["subtitle", "A", "part", "I"] -> [{ type: "subtitle", number: "A" }, { type: "part", number: "I" }]
 */
function parseGroupPath(
  segments: string[]
): { type: string; number: string }[] {
  const pairs: { type: string; number: string }[] = [];
  for (let i = 0; i < segments.length - 1; i += 2) {
    pairs.push({ type: segments[i], number: segments[i + 1] });
  }
  return pairs;
}

/**
 * Walk the children tree to find the target group by path pairs.
 */
function findGroup(
  groups: SectionGroupTree[],
  pairs: { type: string; number: string }[]
): SectionGroupTree | null {
  if (pairs.length === 0) return null;
  const [first, ...rest] = pairs;
  const match = groups.find(
    (g) => g.group_type === first.type && g.number === first.number
  );
  if (!match) return null;
  if (rest.length === 0) return match;
  return findGroup(match.children, rest);
}

/** Group directory page for paths like /titles/26/chapter/1 or /titles/10/subtitle/A/part/I */
export default function GroupDirectoryPage() {
  const params = useParams<{ titleNumber: string; groupPath: string[] }>();
  const titleNumber = Number(params.titleNumber);
  const groupPath = params.groupPath;
  const {
    data: structure,
    isLoading,
    error,
  } = useTitleStructure(titleNumber, true);

  if (isLoading) {
    return <p className="text-gray-500">Loading...</p>;
  }

  if (error || !structure) {
    return <p className="text-red-600">Failed to load title structure.</p>;
  }

  const pairs = parseGroupPath(groupPath);
  const group = findGroup(structure.children ?? [], pairs);

  if (!group) {
    return <p className="text-red-600">Group not found.</p>;
  }

  // Build breadcrumbs
  const breadcrumbs: BreadcrumbSegment[] = [
    { label: `Title ${titleNumber}`, href: `/titles/${titleNumber}` },
  ];
  let pathSoFar = `/titles/${titleNumber}`;
  for (let i = 0; i < pairs.length; i++) {
    const pair = pairs[i];
    pathSoFar += `/${pair.type}/${pair.number}`;
    if (i < pairs.length - 1) {
      breadcrumbs.push({
        label: `${capitalizeGroupType(pair.type)} ${pair.number}`,
        href: pathSoFar,
      });
    } else {
      breadcrumbs.push({
        label: `${capitalizeGroupType(pair.type)} ${pair.number}`,
      });
    }
  }

  const items: DirectoryItem[] = [];

  // Child groups as folders
  for (const child of group.children) {
    const allSections = collectAllSections(child);
    const amendment = latestAmendment(allSections);
    items.push({
      id: `${capitalizeGroupType(child.group_type)} ${child.number}`,
      name: child.name,
      href: `${pathSoFar}/${child.group_type}/${child.number}`,
      kind: 'folder' as const,
      status: detectStatus(child.name),
      sectionCount: allSections.length,
      lastAmendmentLaw: amendment.law,
      lastAmendmentYear: amendment.year,
    });
  }

  // Direct sections as folders (sections expand into CODE + notes sub-files)
  for (const s of group.sections) {
    items.push({
      id: `\u00A7\u2009${s.section_number}`,
      name: s.heading,
      href: `/sections/${titleNumber}/${s.section_number}`,
      kind: 'folder' as const,
      status: s.status ?? detectStatus(s.heading),
      lastAmendmentLaw: s.last_amendment_law ?? null,
      lastAmendmentYear: s.last_amendment_year ?? null,
    });
  }

  return (
    <DirectoryView title={group.name} breadcrumbs={breadcrumbs} items={items} />
  );
}
