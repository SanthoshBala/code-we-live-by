'use client';

import { useParams } from 'next/navigation';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import type {
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

/** Title directory page showing chapters. */
export default function TitleDirectoryPage() {
  const params = useParams<{ titleNumber: string }>();
  const titleNumber = Number(params.titleNumber);
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

  const breadcrumbs: BreadcrumbSegment[] = [{ label: `Title ${titleNumber}` }];

  const items: DirectoryItem[] = structure.chapters.map((ch) => {
    const allSections = [
      ...ch.sections,
      ...ch.subchapters.flatMap((sub) => sub.sections),
    ];
    const amendment = latestAmendment(allSections);
    return {
      id: `Ch. ${ch.chapter_number}`,
      name: ch.chapter_name,
      href: `/titles/${titleNumber}/chapters/${ch.chapter_number}`,
      kind: 'folder' as const,
      sectionCount: allSections.length,
      lastAmendmentLaw: amendment.law,
      lastAmendmentYear: amendment.year,
    };
  });

  return (
    <DirectoryView
      title={structure.title_name}
      breadcrumbs={breadcrumbs}
      items={items}
    />
  );
}
