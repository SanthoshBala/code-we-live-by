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
    Add_Note: 'bg-teal-100 text-teal-800',
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

/** Suppress word-level highlights when the change exceeds this fraction of line length. */
const INLINE_DIFF_THRESHOLD = 0.2;

/**
 * Find amendment-changed text within content, narrowed to just the differing
 * sub-portion when both old_text and new_text exist.
 *
 * For example, old_text="subsection (a) of such section 30" /
 * new_text="subsection (b) of such section 30" highlights only "(a)" or "(b)"
 * rather than the entire phrase.
 */
function findAmendmentRanges(
  content: string,
  amendments: ParsedAmendment[],
  side: 'old' | 'new'
): [number, number][] {
  const ranges: [number, number][] = [];

  for (const a of amendments) {
    const searchText = side === 'old' ? a.old_text : a.new_text;
    if (!searchText) continue;

    // Find where the amendment text appears in the line
    let idx = content.indexOf(searchText);
    if (idx === -1) {
      // Whitespace-normalized fallback
      const normContent = content.replace(/\s+/g, ' ');
      const normText = searchText.replace(/\s+/g, ' ');
      idx = normContent.indexOf(normText);
      if (idx === -1) continue;
    }

    // When both old and new text exist, narrow to just the changed sub-portion
    if (a.old_text && a.new_text) {
      const thisText = side === 'old' ? a.old_text : a.new_text;
      const otherText = side === 'old' ? a.new_text : a.old_text;

      let prefix = 0;
      const minLen = Math.min(thisText.length, otherText.length);
      while (prefix < minLen && thisText[prefix] === otherText[prefix]) {
        prefix++;
      }
      let suffix = 0;
      while (
        suffix < minLen - prefix &&
        thisText[thisText.length - 1 - suffix] ===
          otherText[otherText.length - 1 - suffix]
      ) {
        suffix++;
      }

      const start = prefix;
      const end = thisText.length - suffix;
      if (start < end) {
        // Expand outward to cover full words (non-whitespace runs)
        let wStart = start;
        while (wStart > 0 && thisText[wStart - 1] !== ' ') {
          wStart--;
        }
        let wEnd = end;
        while (wEnd < thisText.length && thisText[wEnd] !== ' ') {
          wEnd++;
        }
        ranges.push([idx + wStart, idx + wEnd]);
        continue;
      }
    }

    // Full text highlight (for add-only or delete-only amendments)
    ranges.push([idx, idx + searchText.length]);
  }

  // Sort by start position and merge overlapping ranges
  if (ranges.length <= 1) return ranges;
  ranges.sort((a, b) => a[0] - b[0]);
  const merged: [number, number][] = [ranges[0]];
  for (let i = 1; i < ranges.length; i++) {
    const prev = merged[merged.length - 1];
    if (ranges[i][0] <= prev[1]) {
      prev[1] = Math.max(prev[1], ranges[i][1]);
    } else {
      merged.push(ranges[i]);
    }
  }
  return merged;
}

/** Render text with highlighted ranges using a darker background. */
function renderHighlightedContent(
  content: string,
  ranges: [number, number][],
  highlightClass: string
): React.ReactNode {
  if (ranges.length === 0) {
    return content;
  }

  const parts: React.ReactNode[] = [];
  let cursor = 0;
  for (let i = 0; i < ranges.length; i++) {
    const [start, end] = ranges[i];
    if (start > cursor) {
      parts.push(content.slice(cursor, start));
    }
    parts.push(
      <span key={i} className={highlightClass}>
        {content.slice(start, end)}
      </span>
    );
    cursor = end;
  }
  if (cursor < content.length) {
    parts.push(content.slice(cursor));
  }
  return <>{parts}</>;
}

/**
 * Suppress inline highlights when the highlighted portion covers more than
 * INLINE_DIFF_THRESHOLD of the line — avoids messy full-line highlights.
 */
function applyHighlightThreshold(
  ranges: [number, number][],
  contentLength: number
): [number, number][] {
  if (ranges.length === 0 || contentLength === 0) return ranges;
  const totalHighlighted = ranges.reduce((sum, [s, e]) => sum + (e - s), 0);
  if (totalHighlighted / contentLength > INLINE_DIFF_THRESHOLD) return [];
  return ranges;
}

/** Renders a single diff line (context, added, or removed) — unified (stacked) mode. */
function UnifiedDiffLineRow({
  line,
  amendments,
  inlineDiffRange,
}: {
  line: DiffLine;
  amendments: ParsedAmendment[];
  inlineDiffRange?: [number, number] | null;
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

  // Prefer amendment text matches (precise), fall back to inline diff (word-level)
  // Apply threshold to suppress highlights covering >20% of line length
  let highlights: [number, number][] = [];
  if (isRemoved || isAdded) {
    const side = isRemoved ? 'old' : 'new';
    const amendmentHits = applyHighlightThreshold(
      findAmendmentRanges(line.content, amendments, side),
      line.content.length
    );
    if (amendmentHits.length > 0) {
      highlights = amendmentHits;
    } else if (inlineDiffRange) {
      highlights = [inlineDiffRange];
    }
  }

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
        {renderHighlightedContent(line.content, highlights, highlightClass)}
      </span>
    </div>
  );
}

/* ---- Paired line helpers (shared between unified & side-by-side) ---- */

/**
 * Compute the character range that differs between two strings.
 * Returns [start, end) for the portion of `b` not shared with `a`,
 * or null if the strings are identical or the change exceeds the
 * highlight threshold (20% of line length, similar to GitHub).
 */
function computeInlineDiff(a: string, b: string): [number, number] | null {
  if (a === b) return null;

  // Find common prefix length
  let prefix = 0;
  const minLen = Math.min(a.length, b.length);
  while (prefix < minLen && a[prefix] === b[prefix]) {
    prefix++;
  }

  // Find common suffix length (not overlapping with prefix)
  let suffix = 0;
  while (
    suffix < minLen - prefix &&
    a[a.length - 1 - suffix] === b[b.length - 1 - suffix]
  ) {
    suffix++;
  }

  const start = prefix;
  let end = b.length - suffix;

  if (start >= end) return null;

  // Trim trailing whitespace from highlight range (cosmetic)
  while (end > start + 1 && b[end - 1] === ' ') {
    end--;
  }

  // Suppress highlighting when too much of the line changed
  const changedLen = end - start;
  if (b.length > 0 && changedLen / b.length > INLINE_DIFF_THRESHOLD) {
    return null;
  }

  return [start, end];
}

/** A paired row for the side-by-side view. */
interface PairedRow {
  left: DiffLine | null;
  right: DiffLine | null;
  /** Inline diff range [start, end) for the left (removed) line. */
  leftHighlight: [number, number] | null;
  /** Inline diff range [start, end) for the right (added) line. */
  rightHighlight: [number, number] | null;
}

/** Pair up removed/added lines from a hunk into side-by-side rows. */
function pairHunkLines(lines: DiffLine[]): PairedRow[] {
  const rows: PairedRow[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.type === 'context') {
      rows.push({
        left: line,
        right: line,
        leftHighlight: null,
        rightHighlight: null,
      });
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
        const leftLine = j < removed.length ? removed[j] : null;
        const rightLine = j < added.length ? added[j] : null;

        // Compute word-level diff for paired removed+added lines
        let leftHL: [number, number] | null = null;
        let rightHL: [number, number] | null = null;
        if (leftLine && rightLine) {
          leftHL = computeInlineDiff(rightLine.content, leftLine.content);
          rightHL = computeInlineDiff(leftLine.content, rightLine.content);
        }

        rows.push({
          left: leftLine,
          right: rightLine,
          leftHighlight: leftHL,
          rightHighlight: rightHL,
        });
      }
    } else {
      rows.push({
        left: null,
        right: line,
        leftHighlight: null,
        rightHighlight: null,
      });
      i++;
    }
  }
  return rows;
}

/** Renders one half (left or right) of a side-by-side row. */
function SideBySideCell({
  line,
  side,
  amendments,
  inlineDiffRange,
}: {
  line: DiffLine | null;
  side: 'left' | 'right';
  amendments: ParsedAmendment[];
  inlineDiffRange?: [number, number] | null;
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

  // Prefer amendment text matches (precise), fall back to inline diff (word-level)
  // Apply threshold to suppress highlights covering >20% of line length
  let highlights: [number, number][] = [];
  if (isRemoved || isAdded) {
    const amendSide = isRemoved ? 'old' : 'new';
    const amendmentHits = applyHighlightThreshold(
      findAmendmentRanges(line.content, amendments, amendSide),
      line.content.length
    );
    if (amendmentHits.length > 0) {
      highlights = amendmentHits;
    } else if (inlineDiffRange) {
      highlights = [inlineDiffRange];
    }
  }

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
        {renderHighlightedContent(line.content, highlights, highlightClass)}
      </span>
    </div>
  );
}

/** Renders a hunk as side-by-side paired columns. */
function SideBySideHunk({
  hunk,
  amendments,
}: {
  hunk: DiffHunk;
  amendments: ParsedAmendment[];
}) {
  const rows = pairHunkLines(hunk.lines);
  return (
    <>
      {rows.map((row, i) => (
        <div key={i} className="grid grid-cols-2 divide-x divide-gray-200">
          <SideBySideCell
            line={row.left}
            side="left"
            amendments={amendments}
            inlineDiffRange={row.leftHighlight}
          />
          <SideBySideCell
            line={row.right}
            side="right"
            amendments={amendments}
            inlineDiffRange={row.rightHighlight}
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
  const amendments = diff.amendments;

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
                    {(() => {
                      const paired = pairHunkLines(region.hunk.lines);
                      // Flatten paired rows back to lines with highlights
                      const linesWithHL: {
                        line: DiffLine;
                        hl: [number, number] | null;
                      }[] = [];
                      for (const row of paired) {
                        if (row.left && row.left.type !== 'context') {
                          linesWithHL.push({
                            line: row.left,
                            hl: row.leftHighlight,
                          });
                        }
                        if (row.right && row.right !== row.left) {
                          linesWithHL.push({
                            line: row.right,
                            hl: row.rightHighlight,
                          });
                        }
                        if (row.left?.type === 'context') {
                          linesWithHL.push({
                            line: row.left,
                            hl: null,
                          });
                        }
                      }
                      return linesWithHL.map((item, li) => (
                        <UnifiedDiffLineRow
                          key={li}
                          line={item.line}
                          amendments={amendments}
                          inlineDiffRange={item.hl}
                        />
                      ));
                    })()}
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
                      amendments={amendments}
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
