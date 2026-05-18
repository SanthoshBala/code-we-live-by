'use client';

import { useParams } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import SectionViewer from '@/components/viewer/SectionViewer';
import RevisionBanner from '@/components/ui/RevisionBanner';
import { useSection } from '@/hooks/useSection';
import { useRevision } from '@/hooks/useRevision';
import type { BreadcrumbSegment, GroupAncestor } from '@/lib/types';

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function buildBreadcrumbs(
  titleNumber: number,
  groupAncestors: GroupAncestor[],
  sectionNumber: string,
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
    label: `§ ${sectionNumber}`,
    href: withRev(basePath),
  });
  crumbs.push({ label: 'CODE' });
  return crumbs;
}

export default function SectionCodePage() {
  const params = useParams<{ titleNumber: string; sectionNumber: string }>();
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
      <SectionViewer
        titleNumber={titleNumber}
        sectionNumber={sectionNumber}
        breadcrumbs={breadcrumbs}
        revision={revision}
      />
    </MainLayout>
  );
}
