'use client';

import { useRef, useState } from 'react';
import type { ParsedAmendment } from '@/lib/types';
import AffectedSectionsTree from './AffectedSectionsTree';

interface LawDiffViewerProps {
  amendments: ParsedAmendment[];
  isLoading: boolean;
}

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

/** Groups amendments by their section_ref display string. */
function groupAmendmentsBySection(
  amendments: ParsedAmendment[]
): Map<string, ParsedAmendment[]> {
  const groups = new Map<string, ParsedAmendment[]>();
  for (const a of amendments) {
    const key = a.section_ref?.display || 'No section reference';
    const list = groups.get(key);
    if (list) {
      list.push(a);
    } else {
      groups.set(key, [a]);
    }
  }
  return groups;
}

/** Side-by-side diff view of parsed amendments. */
export default function LawDiffViewer({
  amendments,
  isLoading,
}: LawDiffViewerProps) {
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const sectionRefs = useRef<Map<string, HTMLDivElement>>(new Map());

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
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  return (
    <div className="flex gap-6">
      {/* Left sidebar — affected sections tree */}
      <div className="hidden w-56 shrink-0 lg:block">
        <div className="sticky top-4">
          <h2 className="mb-2 px-3 text-sm font-semibold text-gray-900">
            Affected Sections
          </h2>
          <AffectedSectionsTree
            amendments={amendments}
            activeSection={activeSection}
            onSectionClick={handleSectionClick}
          />
        </div>
      </div>

      {/* Main panel — amendment cards grouped by section */}
      <div className="min-w-0 flex-1 space-y-6">
        {Array.from(grouped.entries()).map(
          ([sectionKey, sectionAmendments]) => (
            <div
              key={sectionKey}
              ref={(el) => {
                if (el) sectionRefs.current.set(sectionKey, el);
              }}
            >
              <h3 className="mb-3 text-sm font-semibold text-gray-900">
                {sectionKey}
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

                    {/* Card body — diff panels */}
                    <div className="px-4 py-3">
                      {a.old_text || a.new_text ? (
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                          {a.old_text != null && (
                            <div className="rounded bg-red-50 p-3">
                              <div className="mb-1 text-xs font-medium text-red-700">
                                Old Text
                              </div>
                              <pre className="whitespace-pre-wrap font-mono text-xs text-red-900">
                                {a.old_text}
                              </pre>
                            </div>
                          )}
                          {a.new_text != null && (
                            <div className="rounded bg-green-50 p-3">
                              <div className="mb-1 text-xs font-medium text-green-700">
                                New Text
                              </div>
                              <pre className="whitespace-pre-wrap font-mono text-xs text-green-900">
                                {a.new_text}
                              </pre>
                            </div>
                          )}
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
                          <pre className="mt-1 whitespace-pre-wrap rounded bg-gray-50 p-2 font-mono text-xs text-gray-600">
                            {a.context}
                          </pre>
                        </details>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
