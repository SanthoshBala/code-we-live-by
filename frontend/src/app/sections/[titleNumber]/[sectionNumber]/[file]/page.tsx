'use client';

import { useParams } from 'next/navigation';
import { notFound } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import NotesViewer from '@/components/viewer/NotesViewer';
import RevisionBanner from '@/components/ui/RevisionBanner';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import { useRevision } from '@/hooks/useRevision';
import PageHeader from '@/components/ui/PageHeader';
import TabBar from '@/components/ui/TabBar';
import type {
  BreadcrumbSegment,
  SectionGroupTree,
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
  groupAncestors: GroupAncestor[];
}

function findSectionInGroups(
  groups: SectionGroupTree[],
  sectionNumber: string,
  ancestors: GroupAncestor[] = []
): SectionPath | null {
  for (const g of groups) {
    const path = [...ancestors, { type: g.group_type, number: g.number }];
    if (g.sections.some((s) => s.section_number === sectionNumber)) {
      return { groupAncestors: path };
    }
    const nested = findSectionInGroups(g.children, sectionNumber, path);
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
  file: string,
  withRev: (href: string) => string
): BreadcrumbSegment[] {
  if (!structure) return [];

  const basePath = `/sections/${titleNumber}/${sectionNumber}`;
  const crumbs: BreadcrumbSegment[] = [
    { label: `Title ${titleNumber}`, href: withRev(`/titles/${titleNumber}`) },
  ];

  const path = findSectionInGroups(structure.children ?? [], sectionNumber);

  if (path) {
    let pathSoFar = `/titles/${titleNumber}`;
    for (const ancestor of path.groupAncestors) {
      pathSoFar += `/${ancestor.type}/${ancestor.number}`;
      crumbs.push({
        label: `${capitalizeGroupType(ancestor.type)} ${ancestor.number}`,
        href: withRev(pathSoFar),
      });
    }
  }

  crumbs.push({
    label: `\u00A7\u2009${sectionNumber}`,
    href: withRev(basePath),
  });
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
  const { revision, withRev } = useRevision();
  const { data: structure } = useTitleStructure(titleNumber, true, revision);
  const breadcrumbs = buildBreadcrumbs(
    structure,
    titleNumber,
    sectionNumber,
    params.file,
    withRev
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
      {revision !== undefined && <RevisionBanner revision={revision} />}
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
        revision={revision}
      />
    </MainLayout>
  );
}
