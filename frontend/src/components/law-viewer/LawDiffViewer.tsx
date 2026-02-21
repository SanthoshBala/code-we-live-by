'use client';

import Link from 'next/link';
import { useMemo, useRef, useState } from 'react';
import type {
  SectionDiff,
  SectionGroupTree,
  TitleStructure,
} from '@/lib/types';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import AffectedSectionsTree from './AffectedSectionsTree';
import UnifiedDiffCard from './UnifiedDiffCard';

interface LawDiffViewerProps {
  diffs: SectionDiff[];
  isLoading: boolean;
}

/* ---- Breadcrumb helpers ---- */

interface GroupAncestor {
  type: string;
  number: string;
}

function capitalizeGroupType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function findSectionPath(
  groups: SectionGroupTree[],
  sectionNumber: string,
  ancestors: GroupAncestor[] = []
): GroupAncestor[] | null {
  for (const g of groups) {
    const path = [...ancestors, { type: g.group_type, number: g.number }];
    if (g.sections.some((s) => s.section_number === sectionNumber)) {
      return path;
    }
    const nested = findSectionPath(g.children, sectionNumber, path);
    if (nested) return nested;
  }
  return null;
}

/** Build breadcrumb segments for a section within a title structure. */
function buildBreadcrumbSegments(
  structure: TitleStructure,
  sectionNumber: string
): { label: string; href?: string }[] {
  const titleNumber = structure.title_number;
  const crumbs: { label: string; href?: string }[] = [
    { label: `Title ${titleNumber}`, href: `/titles/${titleNumber}` },
  ];

  const path = findSectionPath(structure.children ?? [], sectionNumber);
  if (path) {
    let pathSoFar = `/titles/${titleNumber}`;
    for (const ancestor of path) {
      pathSoFar += `/${ancestor.type}/${ancestor.number}`;
      crumbs.push({
        label: `${capitalizeGroupType(ancestor.type)} ${ancestor.number}`,
        href: pathSoFar,
      });
    }
  }

  crumbs.push({
    label: `\u00A7\u2009${sectionNumber}`,
    href: `/sections/${titleNumber}/${sectionNumber}/CODE`,
  });
  return crumbs;
}

/** Renders a breadcrumb path for a section, fetching title structure lazily. */
function SectionBreadcrumb({
  titleNumber,
  sectionNumber,
}: {
  titleNumber: number;
  sectionNumber: string;
}) {
  const { data: structure } = useTitleStructure(titleNumber, true);

  const segments = useMemo(() => {
    if (!structure) return null;
    return buildBreadcrumbSegments(structure, sectionNumber);
  }, [structure, sectionNumber]);

  if (!segments) {
    return (
      <span className="text-sm font-semibold text-gray-900">
        {titleNumber} U.S.C. &sect; {sectionNumber}
      </span>
    );
  }

  return (
    <nav className="text-sm font-semibold text-gray-900">
      {segments.map((seg, i) => (
        <span key={i}>
          {i > 0 && <span className="mx-1 text-gray-400">/</span>}
          {seg.href ? (
            <Link
              href={seg.href}
              className="hover:text-primary-700 hover:underline"
            >
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

/** Unified diff view of parsed amendments grouped by section. */
export default function LawDiffViewer({
  diffs,
  isLoading,
}: LawDiffViewerProps) {
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const sectionRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const mainPanelRef = useRef<HTMLDivElement>(null);

  // Flatten amendments from all diffs for the sidebar tree
  const allAmendments = useMemo(
    () => diffs.flatMap((d) => d.amendments),
    [diffs]
  );

  if (isLoading) {
    return <p className="text-gray-500">Computing diffs...</p>;
  }

  if (diffs.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-gray-500">
        No amendments parsed from this law.
      </p>
    );
  }

  function handleSectionClick(sectionKey: string) {
    setActiveSection(sectionKey);
    const el = sectionRefs.current.get(sectionKey);
    const container = mainPanelRef.current;
    if (el && container) {
      container.scrollTo({
        top: el.offsetTop - container.offsetTop,
        behavior: 'smooth',
      });
    }
  }

  return (
    <div className="flex h-[calc(100vh-14rem)] gap-6">
      {/* Left sidebar — affected sections tree (independently scrollable) */}
      <div className="hidden w-72 shrink-0 overflow-y-auto lg:block">
        <h2 className="sticky top-0 z-10 mb-2 bg-white px-3 pb-1 text-sm font-semibold text-gray-900">
          Amended Sections
        </h2>
        <AffectedSectionsTree
          amendments={allAmendments}
          activeSection={activeSection}
          onSectionClick={handleSectionClick}
        />
      </div>

      {/* Main panel — unified diff cards per section */}
      <div
        ref={mainPanelRef}
        className="min-w-0 flex-1 space-y-6 overflow-y-auto"
      >
        {diffs.map((diff) => (
          <div
            key={diff.section_key}
            ref={(el) => {
              if (el) sectionRefs.current.set(diff.section_key, el);
            }}
          >
            <h3 className="mb-3">
              <SectionBreadcrumb
                titleNumber={diff.title_number}
                sectionNumber={diff.section_number}
              />
            </h3>
            <UnifiedDiffCard diff={diff} />
          </div>
        ))}
      </div>
    </div>
  );
}
