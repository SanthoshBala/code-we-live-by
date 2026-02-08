'use client';

import { useParams } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import DirectoryView from '@/components/directory/DirectoryView';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import type {
  BreadcrumbSegment,
  ChapterGroupTree,
  DirectoryItem,
  SectionSummary,
  TitleStructure,
} from '@/lib/types';

const NOTE_FILES: { file: string; category: string; label: string }[] = [
  { file: 'EDITORIAL_NOTES', category: 'editorial', label: 'Editorial Notes' },
  {
    file: 'STATUTORY_NOTES',
    category: 'statutory',
    label: 'Statutory Notes',
  },
  {
    file: 'HISTORICAL_NOTES',
    category: 'historical',
    label: 'Historical Notes',
  },
];

interface GroupAncestor {
  type: string;
  number: string;
}

interface SectionPath {
  section: SectionSummary;
  chapterNumber: string;
  subchapterNumber?: string;
  groupAncestors: GroupAncestor[];
}

function findSectionInChapters(
  chapters: {
    chapter_number: string;
    sections: SectionSummary[];
    subchapters: { subchapter_number: string; sections: SectionSummary[] }[];
  }[],
  sectionNumber: string,
  groupAncestors: GroupAncestor[] = []
): SectionPath | null {
  for (const ch of chapters) {
    const direct = ch.sections.find((s) => s.section_number === sectionNumber);
    if (direct) {
      return {
        section: direct,
        chapterNumber: ch.chapter_number,
        groupAncestors,
      };
    }
    for (const sub of ch.subchapters) {
      const inSub = sub.sections.find(
        (s) => s.section_number === sectionNumber
      );
      if (inSub) {
        return {
          section: inSub,
          chapterNumber: ch.chapter_number,
          subchapterNumber: sub.subchapter_number,
          groupAncestors,
        };
      }
    }
  }
  return null;
}

function findSectionInGroups(
  groups: ChapterGroupTree[],
  sectionNumber: string,
  ancestors: GroupAncestor[] = []
): SectionPath | null {
  for (const g of groups) {
    const path = [...ancestors, { type: g.group_type, number: g.group_number }];
    const found = findSectionInChapters(g.chapters, sectionNumber, path);
    if (found) return found;
    const nested = findSectionInGroups(g.child_groups, sectionNumber, path);
    if (nested) return nested;
  }
  return null;
}

function findSection(
  structure: TitleStructure,
  sectionNumber: string
): SectionPath | null {
  return (
    findSectionInChapters(structure.chapters, sectionNumber) ??
    findSectionInGroups(structure.chapter_groups ?? [], sectionNumber)
  );
}

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function buildBreadcrumbs(
  titleNumber: number,
  path: SectionPath | null,
  sectionNumber: string
): BreadcrumbSegment[] {
  const crumbs: BreadcrumbSegment[] = [
    { label: `Title ${titleNumber}`, href: `/titles/${titleNumber}` },
  ];

  if (path) {
    let pathSoFar = `/titles/${titleNumber}`;
    for (const ancestor of path.groupAncestors) {
      pathSoFar += `/${ancestor.type}/${ancestor.number}`;
      crumbs.push({
        label: `${capitalizeGroupType(ancestor.type)} ${ancestor.number}`,
        href: pathSoFar,
      });
    }
    crumbs.push({
      label: `Chapter ${path.chapterNumber}`,
      href: `/titles/${titleNumber}/chapters/${path.chapterNumber}`,
    });
    if (path.subchapterNumber) {
      crumbs.push({
        label: `Subchapter ${path.subchapterNumber}`,
        href: `/titles/${titleNumber}/chapters/${path.chapterNumber}/subchapters/${path.subchapterNumber}`,
      });
    }
  }

  crumbs.push({ label: `\u00A7\u2009${sectionNumber}` });
  return crumbs;
}

export default function SectionDirectoryPage() {
  const params = useParams<{ titleNumber: string; sectionNumber: string }>();
  const titleNumber = Number(params.titleNumber);
  const sectionNumber = decodeURIComponent(params.sectionNumber);
  const { data: structure, isLoading } = useTitleStructure(titleNumber, true);

  const basePath = `/sections/${titleNumber}/${sectionNumber}`;
  const path = structure ? findSection(structure, sectionNumber) : null;
  const breadcrumbs = structure
    ? buildBreadcrumbs(titleNumber, path, sectionNumber)
    : [];

  const heading = path?.section.heading ?? `Section ${sectionNumber}`;
  const noteCategories = path?.section.note_categories ?? [];

  const items: DirectoryItem[] = [
    {
      id: `\u00A7\u2009${sectionNumber}`,
      name: heading,
      href: `${basePath}/CODE`,
      kind: 'file' as const,
      lastAmendmentLaw: path?.section.last_amendment_law ?? null,
      lastAmendmentYear: path?.section.last_amendment_year ?? null,
    },
    ...NOTE_FILES.filter(({ category }) =>
      noteCategories.includes(category)
    ).map(({ file, label }) => ({
      id: file,
      name: label,
      href: `${basePath}/${file}`,
      kind: 'file' as const,
    })),
  ];

  return (
    <MainLayout
      sidebar={
        <Sidebar>
          <TitleList
            activePath={{
              titleNumber,
              sectionNumber,
            }}
          />
        </Sidebar>
      }
    >
      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <DirectoryView
          title={heading}
          breadcrumbs={breadcrumbs}
          items={items}
        />
      )}
    </MainLayout>
  );
}
