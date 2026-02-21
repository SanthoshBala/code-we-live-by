'use client';

import Link from 'next/link';
import { useMemo, useRef, useState } from 'react';
import type {
  ParsedAmendment,
  SectionGroupTree,
  TitleStructure,
} from '@/lib/types';
import { useTitleStructure } from '@/hooks/useTitleStructure';
import AffectedSectionsTree from './AffectedSectionsTree';

interface LawDiffViewerProps {
  amendments: ParsedAmendment[];
  isLoading: boolean;
}

/**
 * Number of "comment" lines the section viewer injects before provisions:
 * fullCitation, heading, "Provisions", and a blank separator line.
 */
const SECTION_HEADER_LINES = 4;

/** Badge with background color based on change type. */
function ChangeTypeBadge({ changeType }: { changeType: string }) {
  const colors: Record<string, string> = {
    Add: 'bg-green-100 text-green-800',
    Modify: 'bg-blue-100 text-blue-800',
    Delete: 'bg-red-100 text-red-800',
    Repeal: 'bg-red-100 text-red-800',
    Redesignate: 'bg-yellow-100 text-yellow-800',
    Transfer: 'bg-purple-100 text-purple-800',
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[changeType] || 'bg-gray-100 text-gray-800'}`}
    >
      {changeType}
    </span>
  );
}

/** Confidence score indicator. */
function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80
      ? 'text-green-700'
      : pct >= 50
        ? 'text-yellow-700'
        : 'text-red-700';
  return <span className={`text-xs ${color}`}>{pct}%</span>;
}

/** Renders a block of text with line numbers in provisions style. */
function DiffBlock({
  text,
  variant,
  startLine,
}: {
  text: string;
  variant: 'old' | 'new';
  startLine: number;
}) {
  const lines = text.split('\n');
  const bg = variant === 'old' ? 'bg-red-100' : 'bg-green-100';
  const textColor = variant === 'old' ? 'text-red-900' : 'text-green-900';
  const gutterColor = variant === 'old' ? 'text-red-400' : 'text-green-600';
  const prefix = variant === 'old' ? '−' : '+';

  return (
    <div
      className={`rounded ${bg} py-2 pr-8 font-mono text-sm leading-relaxed`}
    >
      {lines.map((line, i) => (
        <div key={i} className="flex items-start">
          <span
            className={`w-10 shrink-0 select-none text-right ${gutterColor}`}
          >
            {startLine + i}
          </span>
          <span className={`mx-2 select-none ${gutterColor}`}>│</span>
          <span
            className={`min-w-0 whitespace-pre-wrap pl-[2ch] -indent-[2ch] ${textColor}`}
          >
            <span className="select-none">{prefix} </span>
            {line}
          </span>
        </div>
      ))}
    </div>
  );
}

/** Build a section-level key (no subsection path) for grouping. */
function sectionGroupKey(a: ParsedAmendment): string {
  if (!a.section_ref) return 'No section reference';
  if (a.section_ref.title != null) {
    return `${a.section_ref.title} U.S.C. § ${a.section_ref.section}`;
  }
  return `§ ${a.section_ref.section}`;
}

/** Groups amendments by section (ignoring subsection path). */
function groupAmendmentsBySection(
  amendments: ParsedAmendment[]
): Map<string, ParsedAmendment[]> {
  const groups = new Map<string, ParsedAmendment[]>();
  for (const a of amendments) {
    const key = sectionGroupKey(a);
    const list = groups.get(key);
    if (list) {
      list.push(a);
    } else {
      groups.set(key, [a]);
    }
  }
  return groups;
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
        {titleNumber} U.S.C. § {sectionNumber}
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

/** Parse title and section from a sectionKey like "26 U.S.C. § 219". */
function parseSectionKey(
  key: string
): { titleNumber: number; sectionNumber: string } | null {
  const m = key.match(/^(\d+) U\.S\.C\. § (.+)$/);
  if (!m) return null;
  return { titleNumber: Number(m[1]), sectionNumber: m[2] };
}

/** Side-by-side diff view of parsed amendments. */
export default function LawDiffViewer({
  amendments,
  isLoading,
}: LawDiffViewerProps) {
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const sectionRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const mainPanelRef = useRef<HTMLDivElement>(null);

  if (isLoading) {
    return <p className="text-gray-500">Parsing amendments...</p>;
  }

  if (amendments.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-gray-500">
        No amendments parsed from this law.
      </p>
    );
  }

  const grouped = groupAmendmentsBySection(amendments);

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
          amendments={amendments}
          activeSection={activeSection}
          onSectionClick={handleSectionClick}
        />
      </div>

      {/* Main panel — amendment cards grouped by section (independently scrollable) */}
      <div
        ref={mainPanelRef}
        className="min-w-0 flex-1 space-y-6 overflow-y-auto"
      >
        {Array.from(grouped.entries()).map(
          ([sectionKey, sectionAmendments]) => {
            const parsed = parseSectionKey(sectionKey);
            return (
              <div
                key={sectionKey}
                ref={(el) => {
                  if (el) sectionRefs.current.set(sectionKey, el);
                }}
              >
                <h3 className="mb-3">
                  {parsed ? (
                    <SectionBreadcrumb
                      titleNumber={parsed.titleNumber}
                      sectionNumber={parsed.sectionNumber}
                    />
                  ) : (
                    <span className="text-sm font-semibold text-gray-900">
                      {sectionKey}
                    </span>
                  )}
                </h3>
                <div className="space-y-3">
                  {sectionAmendments.map((a, i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-gray-200 bg-white"
                    >
                      {/* Card header */}
                      <div className="flex flex-wrap items-center gap-2 border-b border-gray-100 px-4 py-2">
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                          {a.pattern_name}
                        </span>
                        <ChangeTypeBadge changeType={a.change_type} />
                        <ConfidenceBadge score={a.confidence} />
                        {a.needs_review && (
                          <span className="text-xs font-medium text-amber-600">
                            Needs Review
                          </span>
                        )}
                        {a.position_qualifier && (
                          <span className="text-xs text-gray-500">
                            {a.position_qualifier.type}
                            {a.position_qualifier.anchor_text &&
                              `: "${a.position_qualifier.anchor_text}"`}
                          </span>
                        )}
                      </div>

                      {/* Card body — side-by-side diff */}
                      <div className="space-y-3 px-4 py-3">
                        {a.old_text != null || a.new_text != null ? (
                          <div className="grid grid-cols-2 gap-3">
                            <DiffBlock
                              text={a.old_text ?? ''}
                              variant="old"
                              startLine={
                                a.start_line
                                  ? a.start_line + SECTION_HEADER_LINES
                                  : 1
                              }
                            />
                            <DiffBlock
                              text={a.new_text ?? ''}
                              variant="new"
                              startLine={
                                a.start_line
                                  ? a.start_line + SECTION_HEADER_LINES
                                  : 1
                              }
                            />
                          </div>
                        ) : (
                          <p className="text-xs italic text-gray-400">
                            No text content extracted
                          </p>
                        )}
                        {a.context && (
                          <details className="mt-2">
                            <summary className="cursor-pointer text-xs text-gray-500">
                              Context
                            </summary>
                            <div className="mt-1 rounded bg-gray-100 py-2 pr-8 font-mono text-sm leading-relaxed">
                              {a.context.split('\n').map((line, ci) => (
                                <div key={ci} className="flex items-start">
                                  <span className="w-10 shrink-0 select-none text-right text-gray-400">
                                    {ci + 1}
                                  </span>
                                  <span className="mx-2 select-none text-gray-400">
                                    │
                                  </span>
                                  <span className="min-w-0 whitespace-pre-wrap text-gray-600">
                                    {line}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </details>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          }
        )}
      </div>
    </div>
  );
}
