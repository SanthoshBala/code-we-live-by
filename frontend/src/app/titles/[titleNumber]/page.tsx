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

function chapterToItem(ch: ChapterTree, titleNumber: number): DirectoryItem {
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
}

/** Title directory page showing chapter groups and ungrouped chapters. */
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

  const items: DirectoryItem[] = [];

  // Groups first
  for (const g of structure.chapter_groups ?? []) {
    const allSections = collectAllSections(g);
    const amendment = latestAmendment(allSections);
    items.push({
      id: `${capitalizeGroupType(g.group_type)} ${g.group_number}`,
      name: `${capitalizeGroupType(g.group_type)} ${g.group_number} \u2014 ${g.group_name}`,
      href: `/titles/${titleNumber}/${g.group_type}/${g.group_number}`,
      kind: 'folder' as const,
      sectionCount: allSections.length,
      lastAmendmentLaw: amendment.law,
      lastAmendmentYear: amendment.year,
    });
  }

  // Ungrouped chapters
  for (const ch of structure.chapters) {
    items.push(chapterToItem(ch, titleNumber));
  }

  return (
    <DirectoryView
      title={structure.title_name}
      breadcrumbs={breadcrumbs}
      items={items}
    />
  );
}
