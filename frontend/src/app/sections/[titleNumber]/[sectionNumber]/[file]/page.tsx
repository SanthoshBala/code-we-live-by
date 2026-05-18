'use client';

import { useParams } from 'next/navigation';
import { notFound } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import NotesViewer from '@/components/viewer/NotesViewer';
import RevisionBanner from '@/components/ui/RevisionBanner';
import { useSection } from '@/hooks/useSection';
import { useRevision } from '@/hooks/useRevision';
import PageHeader from '@/components/ui/PageHeader';
import TabBar from '@/components/ui/TabBar';
import type { BreadcrumbSegment, GroupAncestor } from '@/lib/types';
import Link from 'next/link';

const VALID_FILES: Record<string, string> = {
  EDITORIAL_NOTES: 'Editorial Notes',
  STATUTORY_NOTES: 'Statutory Notes',
  HISTORICAL_NOTES: 'Historical Notes',
};

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
  titleNumber: number,
  groupAncestors: GroupAncestor[],
  sectionNumber: string,
  file: string,
  withRev: (href: string) => string
): BreadcrumbSegment[] {
  const basePath = `/sections/${titleNumber}/${sectionNumber}`;
  const crumbs: BreadcrumbSegment[] = [
    { label: `Title ${titleNumber}`, href: withRev(`/titles/${titleNumber}`) },
  ];

  let pathSoFar = `/titles/${titleNumber}`;
  for (const ancestor of groupAncestors) {
    pathSoFar += `/${ancestor.type}/${ancestor.number}`;
    crumbs.push({
      label: `${capitalizeGroupType(ancestor.type)} ${ancestor.number}`,
      href: withRev(pathSoFar),
    });
  }

  crumbs.push({
    label: `§ ${sectionNumber}`,
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
  const { data: sectionData } = useSection(
    titleNumber,
    sectionNumber,
    revision
  );

  const breadcrumbs = sectionData
    ? buildBreadcrumbs(
        titleNumber,
        sectionData.group_ancestors ?? [],
        sectionNumber,
        params.file,
        withRev
      )
    : [];

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
