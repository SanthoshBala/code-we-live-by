'use client';

import { useParams } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import DirectoryView from '@/components/directory/DirectoryView';
import { useSection } from '@/hooks/useSection';
import { useRevision } from '@/hooks/useRevision';
import type {
  BreadcrumbSegment,
  DirectoryItem,
  GroupAncestor,
  ItemStatus,
} from '@/lib/types';
import { detectStatus } from '@/lib/statusStyles';

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

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function buildBreadcrumbs(
  titleNumber: number,
  groupAncestors: GroupAncestor[],
  sectionNumber: string,
  withRev: (href: string) => string
): BreadcrumbSegment[] {
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

  crumbs.push({ label: `§ ${sectionNumber}` });
  return crumbs;
}

export default function SectionDirectoryPage() {
  const params = useParams<{ titleNumber: string; sectionNumber: string }>();
  const titleNumber = Number(params.titleNumber);
  const sectionNumber = decodeURIComponent(params.sectionNumber);
  const { revision, withRev } = useRevision();
  const { data: sectionData, isLoading } = useSection(
    titleNumber,
    sectionNumber,
    revision
  );

  const basePath = `/sections/${titleNumber}/${sectionNumber}`;

  const heading = sectionData?.heading ?? `Section ${sectionNumber}`;
  const noteCategories: string[] = [
    ...new Set((sectionData?.notes?.notes ?? []).map((n) => n.category)),
  ].sort();
  const status: ItemStatus = sectionData?.is_repealed
    ? 'repealed'
    : detectStatus(heading);
  const lastAmendment = sectionData?.notes?.amendments?.[0] ?? null;
  const lastAmendmentLaw = lastAmendment?.law?.public_law_id ?? null;
  const lastAmendmentYear = lastAmendment?.year ?? null;

  const breadcrumbs = sectionData
    ? buildBreadcrumbs(
        titleNumber,
        sectionData.group_ancestors ?? [],
        sectionNumber,
        withRev
      )
    : [];

  const items: DirectoryItem[] = [
    {
      id: `§ ${sectionNumber}`,
      name: heading,
      href: withRev(`${basePath}/CODE`),
      kind: 'file' as const,
      status,
      lastAmendmentLaw,
      lastAmendmentYear,
    },
    ...NOTE_FILES.filter(({ category }) =>
      noteCategories.includes(category)
    ).map(({ file, label }) => ({
      id: file,
      name: label,
      href: withRev(`${basePath}/${file}`),
      kind: 'file' as const,
      status,
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
          revisionData={sectionData?.last_revision ?? null}
          revision={revision}
        />
      )}
    </MainLayout>
  );
}
