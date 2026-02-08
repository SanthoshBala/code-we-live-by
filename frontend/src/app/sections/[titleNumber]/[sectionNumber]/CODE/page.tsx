'use client';

import { useParams } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import SectionViewer from '@/components/viewer/SectionViewer';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import type { BreadcrumbSegment, TitleStructure } from '@/lib/types';

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

  for (const ch of structure.chapters) {
    if (ch.sections.some((s) => s.section_number === sectionNumber)) {
      crumbs.push({
        label: `Chapter ${ch.chapter_number}`,
        href: `/titles/${titleNumber}/chapters/${ch.chapter_number}`,
      });
      crumbs.push({ label: `\u00A7\u2009${sectionNumber}`, href: basePath });
      crumbs.push({ label: 'CODE' });
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
        crumbs.push({ label: 'CODE' });
        return crumbs;
      }
    }
  }

  crumbs.push({ label: `\u00A7\u2009${sectionNumber}`, href: basePath });
  crumbs.push({ label: 'CODE' });
  return crumbs;
}

export default function SectionCodePage() {
  const params = useParams<{ titleNumber: string; sectionNumber: string }>();
  const titleNumber = Number(params.titleNumber);
  const sectionNumber = params.sectionNumber;
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
