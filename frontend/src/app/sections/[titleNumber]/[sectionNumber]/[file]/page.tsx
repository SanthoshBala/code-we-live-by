'use client';

import { useParams } from 'next/navigation';
import { notFound } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import NotesViewer from '@/components/viewer/NotesViewer';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import PageHeader from '@/components/ui/PageHeader';
import TabBar from '@/components/ui/TabBar';
import type {
  BreadcrumbSegment,
  ChapterGroupTree,
  SectionSummary,
  TitleStructure,
} from '@/lib/types';
import Link from 'next/link';

const VALID_FILES: Record<string, string> = {
  EDITORIAL_NOTES: 'Editorial Notes',
  STATUTORY_NOTES: 'Statutory Notes',
  HISTORICAL_NOTES: 'Historical Notes',
};

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

function Breadcrumbs({ segments }: { segments: BreadcrumbSegment[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mt-1 text-lg text-gray-600">
      {segments.map((seg, i) => (
        <span key={i}>
          {i > 0 && <span className="mx-1">/</span>}
          {seg.href ? (
            <Link href={seg.href} className="hover:text-primary-700">
              {seg.label}
            </Link>
          ) : (
            seg.label
          )}
        </span>
      ))}
    </nav>
  );
}

function buildBreadcrumbs(
  structure: TitleStructure | undefined,
  titleNumber: number,
  sectionNumber: string,
  file: string
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
  crumbs.push({ label: file });
  return crumbs;
}

export default function NoteFilePage() {
  const params = useParams<{
    titleNumber: string;
    sectionNumber: string;
    file: string;
  }>();

  if (!(params.file in VALID_FILES)) {
    notFound();
  }

  const titleNumber = Number(params.titleNumber);
  const sectionNumber = decodeURIComponent(params.sectionNumber);
  const { data: structure } = useTitleStructure(titleNumber, true);
  const breadcrumbs = buildBreadcrumbs(
    structure,
    titleNumber,
    sectionNumber,
    params.file
  );

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
      <PageHeader
        title={VALID_FILES[params.file]}
        subtitle={
          breadcrumbs.length > 0 ? (
            <Breadcrumbs segments={breadcrumbs} />
          ) : undefined
        }
      />
      <TabBar
        tabs={[{ id: 'notes', label: 'Notes' }]}
        activeTab="notes"
        onTabChange={() => {}}
      />
      <NotesViewer
        titleNumber={titleNumber}
        sectionNumber={sectionNumber}
        file={params.file}
      />
    </MainLayout>
  );
}
