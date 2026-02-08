'use client';

import { useParams } from 'next/navigation';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import type { DirectoryItem, BreadcrumbSegment } from '@/lib/types';
import DirectoryView from '@/components/directory/DirectoryView';

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

  const chapter = structure.chapters.find(
    (ch) => ch.chapter_number === chapterNumber
  );
  const subchapter = chapter?.subchapters.find(
    (sub) => sub.subchapter_number === subchapterNumber
  );

  if (!chapter || !subchapter) {
    return <p className="text-red-600">Subchapter not found.</p>;
  }

  const breadcrumbs: BreadcrumbSegment[] = [
    { label: `Title ${titleNumber}`, href: `/titles/${titleNumber}` },
    {
      label: `Chapter ${chapterNumber}`,
      href: `/titles/${titleNumber}/chapters/${chapterNumber}`,
    },
    { label: `Subchapter ${subchapterNumber}` },
  ];

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
