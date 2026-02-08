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
import type { BreadcrumbSegment, TitleStructure } from '@/lib/types';
import Link from 'next/link';

const VALID_FILES: Record<string, string> = {
  EDITORIAL_NOTES: 'Editorial Notes',
  STATUTORY_NOTES: 'Statutory Notes',
  HISTORICAL_NOTES: 'Historical Notes',
};

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

  for (const ch of structure.chapters) {
    if (ch.sections.some((s) => s.section_number === sectionNumber)) {
      crumbs.push({
        label: `Chapter ${ch.chapter_number}`,
        href: `/titles/${titleNumber}/chapters/${ch.chapter_number}`,
      });
      crumbs.push({ label: `\u00A7\u2009${sectionNumber}`, href: basePath });
      crumbs.push({ label: file });
      return crumbs;
    }
    for (const sub of ch.subchapters) {
      if (sub.sections.some((s) => s.section_number === sectionNumber)) {
        crumbs.push({
          label: `Chapter ${ch.chapter_number}`,
          href: `/titles/${titleNumber}/chapters/${ch.chapter_number}`,
        });
        crumbs.push({
          label: `Subchapter ${sub.subchapter_number}`,
          href: `/titles/${titleNumber}/chapters/${ch.chapter_number}/subchapters/${sub.subchapter_number}`,
        });
        crumbs.push({
          label: `\u00A7\u2009${sectionNumber}`,
          href: basePath,
        });
        crumbs.push({ label: file });
        return crumbs;
      }
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
  const sectionNumber = params.sectionNumber;
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
