'use client';

import { useParams } from 'next/navigation';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import { useLatestRevisionForTitle } from '@/hooks/useLatestRevision';
import { useRevision } from '@/hooks/useRevision';
import { revisionLabel } from '@/lib/revisionLabel';
import type {
  SectionGroupTree,
  DirectoryItem,
  SectionSummary,
  BreadcrumbSegment,
} from '@/lib/types';
import { detectStatus } from '@/lib/statusStyles';
import DirectoryView from '@/components/directory/DirectoryView';
import RevisionBanner from '@/components/ui/RevisionBanner';

function latestAmendment(sections: SectionSummary[]): {
  law: string | null;
  year: number | null;
} {
  let latest: { law: string | null; year: number | null } = {
    law: null,
    year: null,
  };
  for (const s of sections) {
    if (
      s.last_amendment_year &&
      (!latest.year || s.last_amendment_year > latest.year)
    ) {
      latest = {
        law: s.last_amendment_law ?? null,
        year: s.last_amendment_year,
      };
    }
  }
  return latest;
}

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function collectAllSections(group: SectionGroupTree): SectionSummary[] {
  const sections: SectionSummary[] = [...group.sections];
  for (const child of group.children) {
    sections.push(...collectAllSections(child));
  }
  return sections;
}

function groupToItem(
  group: SectionGroupTree,
  titleNumber: number,
  parentPath: string,
  withRev: (href: string) => string
): DirectoryItem {
  const allSections = collectAllSections(group);
  const amendment = latestAmendment(allSections);
  return {
    id: `${capitalizeGroupType(group.group_type)} ${group.number}`,
    name: group.name,
    href: withRev(`${parentPath}/${group.group_type}/${group.number}`),
    kind: 'folder' as const,
    status: detectStatus(group.name),
    sectionCount: allSections.length,
    lastAmendmentLaw: amendment.law,
    lastAmendmentYear: amendment.year,
  };
}

/** Title directory page showing child groups and direct sections. */
export default function TitleDirectoryPage() {
  const params = useParams<{ titleNumber: string }>();
  const titleNumber = Number(params.titleNumber);
  const { revision, withRev } = useRevision();
  const {
    data: structure,
    isLoading,
    error,
  } = useTitleStructure(titleNumber, true, revision);
  const { data: latestRevision } = useLatestRevisionForTitle(titleNumber);

  if (isLoading) {
    return <p className="text-gray-500">Loading...</p>;
  }

  if (error || !structure) {
    return <p className="text-red-600">Failed to load title structure.</p>;
  }

  const breadcrumbs: BreadcrumbSegment[] = [{ label: `Title ${titleNumber}` }];
  const basePath = `/titles/${titleNumber}`;

  const items: DirectoryItem[] = [];

  // Child groups as folders
  for (const g of structure.children ?? []) {
    items.push(groupToItem(g, titleNumber, basePath, withRev));
  }

  // Direct sections as folders (sections expand into CODE + notes sub-files)
  for (const s of structure.sections ?? []) {
    items.push({
      id: `\u00A7\u2009${s.section_number}`,
      name: s.heading,
      href: withRev(`/sections/${titleNumber}/${s.section_number}`),
      kind: 'folder' as const,
      status: s.status ?? detectStatus(s.heading),
      lastAmendmentLaw: s.last_amendment_law ?? null,
      lastAmendmentYear: s.last_amendment_year ?? null,
    });
  }

  return (
    <>
      {revision !== undefined && <RevisionBanner revision={revision} />}
      <DirectoryView
        title={structure.title_name}
        breadcrumbs={breadcrumbs}
        items={items}
        revisionLabel={latestRevision ? revisionLabel(latestRevision) : null}
      />
    </>
  );
}
