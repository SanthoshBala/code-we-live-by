'use client';

import { useState, useCallback } from 'react';
import type { SectionDiff, DiffLine, DiffHunk } from '@/lib/types';

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

/** Display line number with SECTION_HEADER_LINES offset for consistency. */
function displayLineNum(ln: number | null): string {
  if (ln == null) return '';
  return String(ln + SECTION_HEADER_LINES);
}

/* ---- Inline amendment-text highlighting ---- */

import type { ParsedAmendment } from '@/lib/types';

/**
 * Find the first occurrence of any search text within content.
 * Returns [start, end) character range, or null if no match.
 * Tries exact match first, then whitespace-normalized match.
 */
function findAmendmentRange(
  content: string,
  searchTexts: (string | null)[]
): [number, number] | null {
  for (const text of searchTexts) {
    if (!text) continue;

    // Exact substring match
    const idx = content.indexOf(text);
    if (idx !== -1) {
      return [idx, idx + text.length];
    }

    // Whitespace-normalized match (amendment text may differ in spacing)
    const normContent = content.replace(/\s+/g, ' ');
    const normText = text.replace(/\s+/g, ' ');
    const normIdx = normContent.indexOf(normText);
    if (normIdx !== -1) {
      return [normIdx, normIdx + normText.length];
    }
  }
  return null;
}

/** Render text with a highlighted range using a darker background. */
function renderHighlightedContent(
  content: string,
  range: [number, number] | null,
  highlightClass: string
): React.ReactNode {
  if (!range || range[0] >= range[1]) {
    return content;
  }
  const [start, end] = range;
  return (
    <>
      {content.slice(0, start)}
      <span className={highlightClass}>{content.slice(start, end)}</span>
      {content.slice(end)}
    </>
  );
}

/** Collect old_text values from amendments for highlighting removed lines. */
function getOldTexts(amendments: ParsedAmendment[]): (string | null)[] {
  return amendments.map((a) => a.old_text);
}

/** Collect new_text values from amendments for highlighting added lines. */
function getNewTexts(amendments: ParsedAmendment[]): (string | null)[] {
  return amendments.map((a) => a.new_text);
}

/** Renders a single diff line (context, added, or removed) — unified (stacked) mode. */
function UnifiedDiffLineRow({
  line,
  amendmentTexts,
}: {
  line: DiffLine;
  amendmentTexts: (string | null)[];
}) {
  const isAdded = line.type === 'added';
  const isRemoved = line.type === 'removed';

  let bg = '';
  let textColor = 'text-gray-800';
  let gutterColor = 'text-gray-400';
  let prefix = ' ';
  let highlightClass = '';

  if (isRemoved) {
    bg = 'bg-red-50';
    textColor = 'text-red-900';
    gutterColor = 'text-red-400';
    prefix = '−';
    highlightClass = 'bg-red-200';
  } else if (isAdded) {
    bg = 'bg-green-50';
    textColor = 'text-green-900';
    gutterColor = 'text-green-600';
    prefix = '+';
    highlightClass = 'bg-green-200';
  }

  const highlight =
    isRemoved || isAdded
      ? findAmendmentRange(line.content, amendmentTexts)
      : null;

  return (
    <div className={`flex items-start ${bg}`}>
      <span
        className={`w-10 shrink-0 select-none text-right font-mono text-xs ${gutterColor}`}
      >
        {isAdded ? '' : displayLineNum(line.old_line_number)}
      </span>
      <span
        className={`w-10 shrink-0 select-none text-right font-mono text-xs ${gutterColor}`}
      >
        {isRemoved ? '' : displayLineNum(line.new_line_number)}
      </span>
      <span className={`mx-1 select-none ${gutterColor}`}>│</span>
      <span
        className={`min-w-0 flex-1 whitespace-pre-wrap pl-[2ch] -indent-[2ch] font-mono text-sm ${textColor}`}
      >
        <span className="select-none">{prefix} </span>
        {renderHighlightedContent(line.content, highlight, highlightClass)}
      </span>
    </div>
  );
}

/* ---- Paired line helpers (shared between unified & side-by-side) ---- */

/** A paired row for the side-by-side view. */
interface PairedRow {
  left: DiffLine | null;
  right: DiffLine | null;
}

/** Pair up removed/added lines from a hunk into side-by-side rows. */
function pairHunkLines(lines: DiffLine[]): PairedRow[] {
  const rows: PairedRow[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.type === 'context') {
      rows.push({ left: line, right: line });
      i++;
    } else if (line.type === 'removed') {
      const removed: DiffLine[] = [];
      while (i < lines.length && lines[i].type === 'removed') {
        removed.push(lines[i]);
        i++;
      }
      const added: DiffLine[] = [];
      while (i < lines.length && lines[i].type === 'added') {
        added.push(lines[i]);
        i++;
      }
      const maxLen = Math.max(removed.length, added.length);
      for (let j = 0; j < maxLen; j++) {
        rows.push({
          left: j < removed.length ? removed[j] : null,
          right: j < added.length ? added[j] : null,
        });
      }
    } else {
      rows.push({ left: null, right: line });
      i++;
    }
  }
  return rows;
}

/** Renders one half (left or right) of a side-by-side row. */
function SideBySideCell({
  line,
  side,
  amendmentTexts,
}: {
  line: DiffLine | null;
  side: 'left' | 'right';
  amendmentTexts: (string | null)[];
}) {
  if (!line) {
    return <div className="flex min-h-[1.5rem] items-start bg-gray-50" />;
  }

  const isRemoved = line.type === 'removed';
  const isAdded = line.type === 'added';

  let bg = '';
  let textColor = 'text-gray-800';
  let gutterColor = 'text-gray-400';
  let prefix = ' ';
  let highlightClass = '';

  if (isRemoved) {
    bg = 'bg-red-50';
    textColor = 'text-red-900';
    gutterColor = 'text-red-400';
    prefix = '−';
    highlightClass = 'bg-red-200';
  } else if (isAdded) {
    bg = 'bg-green-50';
    textColor = 'text-green-900';
    gutterColor = 'text-green-600';
    prefix = '+';
    highlightClass = 'bg-green-200';
  }

  const highlight =
    isRemoved || isAdded
      ? findAmendmentRange(line.content, amendmentTexts)
      : null;

  const lineNum =
    side === 'left'
      ? displayLineNum(line.old_line_number)
      : displayLineNum(line.new_line_number);

  return (
    <div className={`flex items-start ${bg}`}>
      <span
        className={`w-10 shrink-0 select-none text-right font-mono text-xs ${gutterColor}`}
      >
        {lineNum}
      </span>
      <span className={`mx-1 select-none ${gutterColor}`}>│</span>
      <span
        className={`min-w-0 flex-1 whitespace-pre-wrap pl-[2ch] -indent-[2ch] font-mono text-sm ${textColor}`}
      >
        <span className="select-none">{prefix} </span>
        {renderHighlightedContent(line.content, highlight, highlightClass)}
      </span>
    </div>
  );
}

/** Renders a hunk as side-by-side paired columns. */
function SideBySideHunk({
  hunk,
  oldTexts,
  newTexts,
}: {
  hunk: DiffHunk;
  oldTexts: (string | null)[];
  newTexts: (string | null)[];
}) {
  const rows = pairHunkLines(hunk.lines);
  return (
    <>
      {rows.map((row, i) => (
        <div key={i} className="grid grid-cols-2 divide-x divide-gray-200">
          <SideBySideCell
            line={row.left}
            side="left"
            amendmentTexts={oldTexts}
          />
          <SideBySideCell
            line={row.right}
            side="right"
            amendmentTexts={newTexts}
          />
        </div>
      ))}
    </>
  );
}

/** Clickable row to expand hidden lines between/around hunks. */
function ExpanderRow({
  count,
  onClick,
}: {
  count: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center bg-blue-50 px-2 py-1 text-xs text-blue-600 hover:bg-blue-100"
    >
      <span className="w-[5.25rem] shrink-0" />
      <span className="mx-1 select-none text-blue-300">│</span>
      <span>
        ⋯ {count} hidden line{count !== 1 ? 's' : ''} — click to expand
      </span>
    </button>
  );
}

/** Renders expanded lines from all_provisions — unified (stacked) mode. */
function UnifiedExpandedLines({ lines }: { lines: DiffLine[] }) {
  return (
    <>
      {lines.map((line, i) => (
        <div key={i} className="flex items-start bg-gray-50">
          <span className="w-10 shrink-0 select-none text-right font-mono text-xs text-gray-300">
            {displayLineNum(line.old_line_number)}
          </span>
          <span className="w-10 shrink-0 select-none text-right font-mono text-xs text-gray-300">
            {displayLineNum(line.new_line_number)}
          </span>
          <span className="mx-1 select-none text-gray-300">│</span>
          <span className="min-w-0 flex-1 whitespace-pre-wrap pl-[2ch] -indent-[2ch] font-mono text-sm text-gray-500">
            <span className="select-none">&nbsp; </span>
            {line.content}
          </span>
        </div>
      ))}
    </>
  );
}

/** Renders expanded lines — side-by-side mode (identical content both sides). */
function SideBySideExpandedLines({ lines }: { lines: DiffLine[] }) {
  return (
    <>
      {lines.map((line, i) => (
        <div key={i} className="grid grid-cols-2 divide-x divide-gray-200">
          <div className="flex items-start bg-gray-50">
            <span className="w-10 shrink-0 select-none text-right font-mono text-xs text-gray-300">
              {displayLineNum(line.old_line_number)}
            </span>
            <span className="mx-1 select-none text-gray-300">│</span>
            <span className="min-w-0 flex-1 whitespace-pre-wrap pl-[2ch] -indent-[2ch] font-mono text-sm text-gray-500">
              <span className="select-none">&nbsp; </span>
              {line.content}
            </span>
          </div>
          <div className="flex items-start bg-gray-50">
            <span className="w-10 shrink-0 select-none text-right font-mono text-xs text-gray-300">
              {displayLineNum(line.new_line_number)}
            </span>
            <span className="mx-1 select-none text-gray-300">│</span>
            <span className="min-w-0 flex-1 whitespace-pre-wrap pl-[2ch] -indent-[2ch] font-mono text-sm text-gray-500">
              <span className="select-none">&nbsp; </span>
              {line.content}
            </span>
          </div>
        </div>
      ))}
    </>
  );
}

interface UnifiedDiffCardProps {
  diff: SectionDiff;
}

/**
 * Renders a single SectionDiff as a GitHub-style unified diff card.
 *
 * Shows amendment badges in a header, diff hunks with context/added/removed
 * lines, and expandable regions between hunks to reveal the full section.
 */
export default function UnifiedDiffCard({ diff }: UnifiedDiffCardProps) {
  // Amendment old/new texts for inline highlighting
  const oldTexts = getOldTexts(diff.amendments);
  const newTexts = getNewTexts(diff.amendments);

  // Track which collapsed regions are expanded, keyed by region index
  const [expandedRegions, setExpandedRegions] = useState<Set<number>>(
    new Set()
  );

  const toggleRegion = useCallback((regionIndex: number) => {
    setExpandedRegions((prev) => {
      const next = new Set(prev);
      if (next.has(regionIndex)) {
        next.delete(regionIndex);
      } else {
        next.add(regionIndex);
      }
      return next;
    });
  }, []);

  // Deduplicate change types for badges
  const changeTypes = [...new Set(diff.amendments.map((a) => a.change_type))];

  // Build collapsed regions between/around hunks
  // Each region is identified by: regionIndex, startProvisionIdx, endProvisionIdx
  type Region =
    | { type: 'hunk'; hunk: DiffHunk }
    | {
        type: 'collapsed';
        regionIndex: number;
        startIdx: number;
        endIdx: number;
      };

  const regions: Region[] = [];
  let regionCounter = 0;

  // Provision indices are 0-based; line_numbers are 1-based.
  // all_provisions is the "after" state, so map by new_line_number.
  const provisionNewLineToIdx = new Map<number, number>();
  diff.all_provisions.forEach((p, idx) => {
    if (p.new_line_number != null) {
      provisionNewLineToIdx.set(p.new_line_number, idx);
    }
  });

  if (diff.hunks.length === 0) {
    // No hunks — show amendments metadata only
  } else {
    let lastEndIdx = -1; // last provision index covered by a hunk

    for (let h = 0; h < diff.hunks.length; h++) {
      const hunk = diff.hunks[h];

      // Find the provision index range for this hunk using new_line_number
      // (works for context and added lines; removed lines don't appear in after)
      const hunkNewLines = hunk.lines.filter((l) => l.type !== 'removed');
      const firstNewLine = hunkNewLines[0]?.new_line_number;
      const lastNewLine =
        hunkNewLines[hunkNewLines.length - 1]?.new_line_number;

      const hunkStartIdx =
        firstNewLine != null
          ? (provisionNewLineToIdx.get(firstNewLine) ?? 0)
          : 0;
      const hunkEndIdx =
        lastNewLine != null
          ? (provisionNewLineToIdx.get(lastNewLine) ??
            diff.all_provisions.length - 1)
          : diff.all_provisions.length - 1;

      // Collapsed region before this hunk
      const gapStart = lastEndIdx + 1;
      const gapEnd = hunkStartIdx - 1;
      if (gapEnd >= gapStart) {
        const ri = regionCounter++;
        regions.push({
          type: 'collapsed',
          regionIndex: ri,
          startIdx: gapStart,
          endIdx: gapEnd,
        });
      }

      regions.push({ type: 'hunk', hunk });
      lastEndIdx = hunkEndIdx;
    }

    // Collapsed region after the last hunk
    if (lastEndIdx < diff.all_provisions.length - 1) {
      const ri = regionCounter++;
      regions.push({
        type: 'collapsed',
        regionIndex: ri,
        startIdx: lastEndIdx + 1,
        endIdx: diff.all_provisions.length - 1,
      });
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {/* Card header — amendment badges */}
      <div className="flex flex-wrap items-center gap-2 border-b border-gray-100 px-4 py-2">
        {changeTypes.map((ct) => (
          <ChangeTypeBadge key={ct} changeType={ct} />
        ))}
        {diff.amendments.map((a, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700"
          >
            {a.pattern_name}
            <ConfidenceBadge score={a.confidence} />
          </span>
        ))}
        {diff.amendments.some((a) => a.needs_review) && (
          <span className="text-xs font-medium text-amber-600">
            Needs Review
          </span>
        )}
      </div>

      {/* Diff body */}
      {diff.hunks.length === 0 ? (
        <div className="px-4 py-3">
          <p className="text-xs italic text-gray-400">
            No text changes detected (may be a structural change)
          </p>
        </div>
      ) : (
        <>
          {/* Unified (stacked) view — mobile only */}
          <div className="leading-relaxed lg:hidden">
            {regions.map((region, idx) => {
              if (region.type === 'hunk') {
                return (
                  <div key={`hunk-${idx}`}>
                    <div className="bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-500">
                      @@ lines {region.hunk.old_start + SECTION_HEADER_LINES}–
                      {region.hunk.old_start +
                        SECTION_HEADER_LINES +
                        region.hunk.lines.filter((l) => l.type !== 'added')
                          .length -
                        1}{' '}
                      @@
                    </div>
                    {region.hunk.lines.map((line, li) => (
                      <UnifiedDiffLineRow
                        key={li}
                        line={line}
                        amendmentTexts={
                          line.type === 'removed' ? oldTexts : newTexts
                        }
                      />
                    ))}
                  </div>
                );
              }

              const count = region.endIdx - region.startIdx + 1;
              if (expandedRegions.has(region.regionIndex)) {
                return (
                  <UnifiedExpandedLines
                    key={`expanded-${region.regionIndex}`}
                    lines={diff.all_provisions.slice(
                      region.startIdx,
                      region.endIdx + 1
                    )}
                  />
                );
              }
              return (
                <ExpanderRow
                  key={`expander-${region.regionIndex}`}
                  count={count}
                  onClick={() => toggleRegion(region.regionIndex)}
                />
              );
            })}
          </div>

          {/* Side-by-side view — desktop only */}
          <div className="hidden leading-relaxed lg:block">
            {regions.map((region, idx) => {
              if (region.type === 'hunk') {
                return (
                  <div key={`hunk-${idx}`}>
                    <div className="grid grid-cols-2 divide-x divide-gray-200 bg-gray-100 font-mono text-xs text-gray-500">
                      <div className="px-2 py-0.5">
                        @@ lines {region.hunk.old_start + SECTION_HEADER_LINES}–
                        {region.hunk.old_start +
                          SECTION_HEADER_LINES +
                          region.hunk.lines.filter((l) => l.type !== 'added')
                            .length -
                          1}{' '}
                        @@
                      </div>
                      <div className="px-2 py-0.5">
                        @@ lines {region.hunk.new_start + SECTION_HEADER_LINES}–
                        {region.hunk.new_start +
                          SECTION_HEADER_LINES +
                          region.hunk.lines.filter((l) => l.type !== 'removed')
                            .length -
                          1}{' '}
                        @@
                      </div>
                    </div>
                    <SideBySideHunk
                      hunk={region.hunk}
                      oldTexts={oldTexts}
                      newTexts={newTexts}
                    />
                  </div>
                );
              }

              const count = region.endIdx - region.startIdx + 1;
              if (expandedRegions.has(region.regionIndex)) {
                return (
                  <SideBySideExpandedLines
                    key={`expanded-${region.regionIndex}`}
                    lines={diff.all_provisions.slice(
                      region.startIdx,
                      region.endIdx + 1
                    )}
                  />
                );
              }
              return (
                <ExpanderRow
                  key={`expander-${region.regionIndex}`}
                  count={count}
                  onClick={() => toggleRegion(region.regionIndex)}
                />
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
