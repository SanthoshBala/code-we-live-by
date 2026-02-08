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

function findChapterInGroups(
  groups: ChapterGroupTree[],
  chapterNumber: string
): ChapterTree | undefined {
  for (const g of groups) {
    const found = g.chapters.find((ch) => ch.chapter_number === chapterNumber);
    if (found) return found;
    const nested = findChapterInGroups(g.child_groups, chapterNumber);
    if (nested) return nested;
  }
  return undefined;
}

/** Chapter directory page showing subchapters and sections. */
export default function ChapterDirectoryPage() {
  const params = useParams<{ titleNumber: string; chapterNumber: string }>();
  const titleNumber = Number(params.titleNumber);
  const chapterNumber = params.chapterNumber;
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

  const chapter =
    structure.chapters.find((ch) => ch.chapter_number === chapterNumber) ??
    findChapterInGroups(structure.chapter_groups ?? [], chapterNumber);

  if (!chapter) {
    return <p className="text-red-600">Chapter not found.</p>;
  }

  const breadcrumbs: BreadcrumbSegment[] = [
    { label: `Title ${titleNumber}`, href: `/titles/${titleNumber}` },
    { label: `Chapter ${chapterNumber}` },
  ];

  const items: DirectoryItem[] = [
    ...chapter.subchapters.map((sub) => {
      const amendment = latestAmendment(sub.sections);
      return {
        id: `Subch. ${sub.subchapter_number}`,
        name: sub.subchapter_name,
        href: `/titles/${titleNumber}/chapters/${chapterNumber}/subchapters/${sub.subchapter_number}`,
        kind: 'folder' as const,
        sectionCount: sub.sections.length,
        lastAmendmentLaw: amendment.law,
        lastAmendmentYear: amendment.year,
      };
    }),
    ...chapter.sections.map((s) => ({
      id: `\u00A7\u2009${s.section_number}`,
      name: s.heading,
      href: `/sections/${titleNumber}/${s.section_number}`,
      kind: 'file' as const,
      lastAmendmentLaw: s.last_amendment_law ?? null,
      lastAmendmentYear: s.last_amendment_year ?? null,
    })),
  ];

  return (
    <DirectoryView
      title={chapter.chapter_name}
      breadcrumbs={breadcrumbs}
      items={items}
    />
  );
}
