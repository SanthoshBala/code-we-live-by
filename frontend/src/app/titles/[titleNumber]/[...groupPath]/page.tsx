'use client';

import { useParams } from 'next/navigation';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import type {
  ChapterGroupTree,
  ChapterTree,
  DirectoryItem,
  SectionSummary,
  BreadcrumbSegment,
} from '@/lib/types';
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

function collectAllSections(group: ChapterGroupTree): SectionSummary[] {
  const sections: SectionSummary[] = [];
  for (const ch of group.chapters) {
    sections.push(...ch.sections);
    for (const sub of ch.subchapters) {
      sections.push(...sub.sections);
    }
  }
  for (const cg of group.child_groups) {
    sections.push(...collectAllSections(cg));
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
 * Walk the chapter_groups tree to find the target group by path pairs.
 */
function findGroup(
  groups: ChapterGroupTree[],
  pairs: { type: string; number: string }[]
): ChapterGroupTree | null {
  if (pairs.length === 0) return null;
  const [first, ...rest] = pairs;
  const match = groups.find(
    (g) => g.group_type === first.type && g.group_number === first.number
  );
  if (!match) return null;
  if (rest.length === 0) return match;
  return findGroup(match.child_groups, rest);
}

/** Group directory page for paths like /titles/26/subtitle/A or /titles/10/subtitle/A/part/I */
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
  const group = findGroup(structure.chapter_groups ?? [], pairs);

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
  for (const cg of group.child_groups) {
    const allSections = collectAllSections(cg);
    const amendment = latestAmendment(allSections);
    items.push({
      id: `${capitalizeGroupType(cg.group_type)} ${cg.group_number}`,
      name: `${capitalizeGroupType(cg.group_type)} ${cg.group_number} \u2014 ${cg.group_name}`,
      href: `${pathSoFar}/${cg.group_type}/${cg.group_number}`,
      kind: 'folder' as const,
      sectionCount: allSections.length,
      lastAmendmentLaw: amendment.law,
      lastAmendmentYear: amendment.year,
    });
  }

  // Chapters as folders
  for (const ch of group.chapters) {
    const allSections = [
      ...ch.sections,
      ...ch.subchapters.flatMap((sub) => sub.sections),
    ];
    const amendment = latestAmendment(allSections);
    items.push({
      id: `Ch. ${ch.chapter_number}`,
      name: ch.chapter_name,
      href: `/titles/${titleNumber}/chapters/${ch.chapter_number}`,
      kind: 'folder' as const,
      sectionCount: allSections.length,
      lastAmendmentLaw: amendment.law,
      lastAmendmentYear: amendment.year,
    });
  }

  return (
    <DirectoryView
      title={group.group_name}
      breadcrumbs={breadcrumbs}
      items={items}
    />
  );
}
