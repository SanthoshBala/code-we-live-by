'use client';

import { useParams } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import SectionViewer from '@/components/viewer/SectionViewer';
import RevisionBanner from '@/components/ui/RevisionBanner';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import { useRevision } from '@/hooks/useRevision';
import type {
  BreadcrumbSegment,
  SectionGroupTree,
  SectionSummary,
  TitleStructure,
} from '@/lib/types';

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

function buildBreadcrumbs(
  structure: TitleStructure | undefined,
  titleNumber: number,
  sectionNumber: string,
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
  crumbs.push({ label: 'CODE' });
  return crumbs;
}

export default function SectionCodePage() {
  const params = useParams<{ titleNumber: string; sectionNumber: string }>();
  const titleNumber = Number(params.titleNumber);
  const sectionNumber = decodeURIComponent(params.sectionNumber);
  const { revision, withRev } = useRevision();
  const { data: structure } = useTitleStructure(titleNumber, true, revision);

  const breadcrumbs = buildBreadcrumbs(
    structure,
    titleNumber,
    sectionNumber,
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
      <SectionViewer
        titleNumber={titleNumber}
        sectionNumber={sectionNumber}
        breadcrumbs={breadcrumbs}
        revision={revision}
      />
    </MainLayout>
  );
}
