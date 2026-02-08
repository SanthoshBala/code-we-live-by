'use client';

import { useParams } from 'next/navigation';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import type {
  ChapterGroupTree,
  ChapterTree,
  DirectoryItem,
  BreadcrumbSegment,
} from '@/lib/types';
import DirectoryView from '@/components/directory/DirectoryView';

interface GroupAncestor {
  type: string;
  number: string;
}

interface ChapterWithAncestors {
  chapter: ChapterTree;
  ancestors: GroupAncestor[];
}

function findChapterInGroups(
  groups: ChapterGroupTree[],
  chapterNumber: string,
  ancestors: GroupAncestor[] = []
): ChapterWithAncestors | undefined {
  for (const g of groups) {
    const path = [...ancestors, { type: g.group_type, number: g.group_number }];
    const found = g.chapters.find((ch) => ch.chapter_number === chapterNumber);
    if (found) return { chapter: found, ancestors: path };
    const nested = findChapterInGroups(g.child_groups, chapterNumber, path);
    if (nested) return nested;
  }
  return undefined;
}

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

/** Subchapter directory page showing sections. */
export default function SubchapterDirectoryPage() {
  const params = useParams<{
    titleNumber: string;
    chapterNumber: string;
    subchapterNumber: string;
  }>();
  const titleNumber = Number(params.titleNumber);
  const chapterNumber = params.chapterNumber;
  const subchapterNumber = params.subchapterNumber;
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

  const ungrouped = structure.chapters.find(
    (ch) => ch.chapter_number === chapterNumber
  );
  const grouped = ungrouped
    ? undefined
    : findChapterInGroups(structure.chapter_groups ?? [], chapterNumber);
  const chapter = ungrouped ?? grouped?.chapter;
  const subchapter = chapter?.subchapters.find(
    (sub) => sub.subchapter_number === subchapterNumber
  );

  if (!chapter || !subchapter) {
    return <p className="text-red-600">Subchapter not found.</p>;
  }

  const breadcrumbs: BreadcrumbSegment[] = [
    { label: `Title ${titleNumber}`, href: `/titles/${titleNumber}` },
  ];
  if (grouped) {
    let pathSoFar = `/titles/${titleNumber}`;
    for (const ancestor of grouped.ancestors) {
      pathSoFar += `/${ancestor.type}/${ancestor.number}`;
      breadcrumbs.push({
        label: `${capitalizeGroupType(ancestor.type)} ${ancestor.number}`,
        href: pathSoFar,
      });
    }
  }
  breadcrumbs.push({
    label: `Chapter ${chapterNumber}`,
    href: `/titles/${titleNumber}/chapters/${chapterNumber}`,
  });
  breadcrumbs.push({ label: `Subchapter ${subchapterNumber}` });

  const items: DirectoryItem[] = subchapter.sections.map((s) => ({
    id: `\u00A7\u2009${s.section_number}`,
    name: s.heading,
    href: `/sections/${titleNumber}/${s.section_number}`,
    kind: 'file' as const,
    lastAmendmentLaw: s.last_amendment_law ?? null,
    lastAmendmentYear: s.last_amendment_year ?? null,
  }));

  return (
    <DirectoryView
      title={subchapter.subchapter_name}
      breadcrumbs={breadcrumbs}
      items={items}
    />
  );
}
