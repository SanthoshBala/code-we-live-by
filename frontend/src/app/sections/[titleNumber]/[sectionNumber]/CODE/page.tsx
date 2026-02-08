'use client';

import { useParams } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import SectionViewer from '@/components/viewer/SectionViewer';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import type {
  BreadcrumbSegment,
  ChapterGroupTree,
  SectionSummary,
  TitleStructure,
} from '@/lib/types';

interface GroupAncestor {
  type: string;
  number: string;
}

interface SectionPath {
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
    if (ch.sections.some((s) => s.section_number === sectionNumber)) {
      return { chapterNumber: ch.chapter_number, groupAncestors };
    }
    for (const sub of ch.subchapters) {
      if (sub.sections.some((s) => s.section_number === sectionNumber)) {
        return {
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

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function buildBreadcrumbs(
  structure: TitleStructure | undefined,
  titleNumber: number,
  sectionNumber: string
): BreadcrumbSegment[] {
  if (!structure) return [];

  const basePath = `/sections/${titleNumber}/${sectionNumber}`;
  const crumbs: BreadcrumbSegment[] = [
    { label: `Title ${titleNumber}`, href: `/titles/${titleNumber}` },
  ];

  const path =
    findSectionInChapters(structure.chapters, sectionNumber) ??
    findSectionInGroups(structure.chapter_groups ?? [], sectionNumber);

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

  crumbs.push({ label: `\u00A7\u2009${sectionNumber}`, href: basePath });
  crumbs.push({ label: 'CODE' });
  return crumbs;
}

export default function SectionCodePage() {
  const params = useParams<{ titleNumber: string; sectionNumber: string }>();
  const titleNumber = Number(params.titleNumber);
  const sectionNumber = decodeURIComponent(params.sectionNumber);
  const { data: structure } = useTitleStructure(titleNumber, true);

  const breadcrumbs = buildBreadcrumbs(structure, titleNumber, sectionNumber);

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
      <SectionViewer
        titleNumber={titleNumber}
        sectionNumber={sectionNumber}
        breadcrumbs={breadcrumbs}
      />
    </MainLayout>
  );
}
