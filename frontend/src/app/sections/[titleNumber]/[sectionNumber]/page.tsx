'use client';

import { useParams } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import DirectoryView from '@/components/directory/DirectoryView';
import RevisionBanner from '@/components/ui/RevisionBanner';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import { useSection } from '@/hooks/useSection';
import { useRevision } from '@/hooks/useRevision';
import { revisionLabel } from '@/lib/revisionLabel';
import type {
  BreadcrumbSegment,
  DirectoryItem,
  ItemStatus,
  SectionGroupTree,
  SectionSummary,
  TitleStructure,
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

interface GroupAncestor {
  type: string;
  number: string;
}

interface SectionPath {
  section: SectionSummary;
  groupAncestors: GroupAncestor[];
}

function findSectionInGroups(
  groups: SectionGroupTree[],
  sectionNumber: string,
  ancestors: GroupAncestor[] = []
): SectionPath | null {
  for (const g of groups) {
    const path = [...ancestors, { type: g.group_type, number: g.number }];
    // Check direct sections
    const direct = g.sections.find((s) => s.section_number === sectionNumber);
    if (direct) {
      return { section: direct, groupAncestors: path };
    }
    // Recurse into children
    const nested = findSectionInGroups(g.children, sectionNumber, path);
    if (nested) return nested;
  }
  return null;
}

function findSection(
  structure: TitleStructure,
  sectionNumber: string
): SectionPath | null {
  // Check direct sections on the title
  const direct = (structure.sections ?? []).find(
    (s) => s.section_number === sectionNumber
  );
  if (direct) {
    return { section: direct, groupAncestors: [] };
  }
  return findSectionInGroups(structure.children ?? [], sectionNumber);
}

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function buildBreadcrumbs(
  titleNumber: number,
  path: SectionPath | null,
  sectionNumber: string,
  withRev: (href: string) => string
): BreadcrumbSegment[] {
  const crumbs: BreadcrumbSegment[] = [
    { label: `Title ${titleNumber}`, href: withRev(`/titles/${titleNumber}`) },
  ];

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

  crumbs.push({ label: `\u00A7\u2009${sectionNumber}` });
  return crumbs;
}

export default function SectionDirectoryPage() {
  const params = useParams<{ titleNumber: string; sectionNumber: string }>();
  const titleNumber = Number(params.titleNumber);
  const sectionNumber = decodeURIComponent(params.sectionNumber);
  const { revision, withRev } = useRevision();
  const { data: structure, isLoading } = useTitleStructure(
    titleNumber,
    true,
    revision
  );
  const { data: sectionData } = useSection(
    titleNumber,
    sectionNumber,
    revision
  );

  const basePath = `/sections/${titleNumber}/${sectionNumber}`;
  const path = structure ? findSection(structure, sectionNumber) : null;
  const breadcrumbs = structure
    ? buildBreadcrumbs(titleNumber, path, sectionNumber, withRev)
    : [];

  const heading = path?.section.heading ?? `Section ${sectionNumber}`;
  const noteCategories = path?.section.note_categories ?? [];
  const status: ItemStatus = path?.section.status ?? detectStatus(heading);

  const items: DirectoryItem[] = [
    {
      id: `\u00A7\u2009${sectionNumber}`,
      name: heading,
      href: withRev(`${basePath}/CODE`),
      kind: 'file' as const,
      status,
      lastAmendmentLaw: path?.section.last_amendment_law ?? null,
      lastAmendmentYear: path?.section.last_amendment_year ?? null,
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
      {revision !== undefined && <RevisionBanner revision={revision} />}
      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <DirectoryView
          title={heading}
          breadcrumbs={breadcrumbs}
          items={items}
          revisionLabel={
            sectionData?.last_revision
              ? revisionLabel(sectionData.last_revision)
              : null
          }
        />
      )}
    </MainLayout>
  );
}
