'use client';

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import type { CodeLine, ItemStatus } from '@/lib/types';
import { statusMessage } from '@/lib/statusStyles';

interface SectionProvisionsProps {
  fullCitation: string;
  heading: string;
  textContent: string | null;
  provisions: CodeLine[] | null;
  status: ItemStatus;
}

// Legacy heuristic fallback — used when structured provisions are not available.
// Will be removed after all sections are re-ingested with normalized_provisions.
function isHeaderLine(text: string): boolean {
  if (!/^\([a-zA-Z0-9]+\)/.test(text)) return false;
  if (text.length > 200) return false;
  if (/[.;,:—]$/.test(text)) return false;
  if (/\b(or|and)$/.test(text)) return false;
  return true;
}

const headerMarkerClass = 'text-primary-600';
const headerTitleClass = 'font-bold text-primary-700';

function provisionsToParseLines(provisions: CodeLine[]): ParsedLine[] {
  return provisions.map((line) => ({
    lineIndex: line.line_number - 1,
    indent: '\t'.repeat(line.indent_level),
    text: line.content,
    isListItem: line.marker !== null,
    isHeader: line.is_header,
  }));
}

/* ---- Tree-building types & helpers ---- */

interface ParsedLine {
  lineIndex: number;
  indent: string;
  text: string;
  isListItem: boolean;
  isHeader: boolean;
}

interface Section {
  header: ParsedLine;
  depth: number;
  children: (ParsedLine | Section)[];
}

type TreeNode = ParsedLine | Section;

function isSection(node: TreeNode): node is Section {
  return 'depth' in node;
}

function indentLength(indent: string): number {
  return indent.replace(/\t/g, '    ').length;
}

function buildSections(parsedLines: ParsedLine[]): TreeNode[] {
  const root: TreeNode[] = [];
  const stack: Section[] = [];

  for (const pl of parsedLines) {
    if (pl.isHeader) {
      const len = indentLength(pl.indent);
      while (stack.length > 0) {
        const top = stack[stack.length - 1];
        if (indentLength(top.header.indent) >= len) {
          stack.pop();
        } else {
          break;
        }
      }
      const section: Section = {
        header: pl,
        depth: stack.length,
        children: [],
      };
      if (stack.length > 0) {
        stack[stack.length - 1].children.push(section);
      } else {
        root.push(section);
      }
      stack.push(section);
    } else {
      if (stack.length > 0) {
        stack[stack.length - 1].children.push(pl);
      } else {
        root.push(pl);
      }
    }
  }
  return root;
}

/* ---- Component ---- */

/** Renders the operative law text as numbered lines like a code file. */
export default function SectionProvisions({
  fullCitation,
  heading,
  textContent,
  provisions,
  status,
}: SectionProvisionsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const headerRefs = useRef(new Map<number, HTMLDivElement>());
  const [headerHeights, setHeaderHeights] = useState(new Map<number, number>());

  // Measure actual header heights so sub-headers stack below parents
  // regardless of text wrapping.
  const measureHeaders = useCallback(() => {
    setHeaderHeights((prev) => {
      const next = new Map<number, number>();
      headerRefs.current.forEach((el, key) => {
        next.set(key, Math.round(el.getBoundingClientRect().height));
      });
      if (next.size === prev.size) {
        let same = true;
        for (const [key, value] of next) {
          if (prev.get(key) !== value) {
            same = false;
            break;
          }
        }
        if (same) return prev;
      }
      return next;
    });
  }, []);

  // Measure before first paint so offsets are correct immediately.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useLayoutEffect(measureHeaders, [textContent, provisions]);

  // Re-measure when the container resizes (viewport width changes
  // cause header text to re-wrap).
  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(measureHeaders);
    ro.observe(container);
    return () => ro.disconnect();
  }, [measureHeaders]);

  if (!textContent) {
    return (
      <div className="rounded border border-gray-200 bg-gray-50 px-4 py-6 text-center text-sm text-gray-500">
        {statusMessage(status)}
      </div>
    );
  }

  const docstring = [fullCitation, heading, 'Provisions'];
  const blankLineNumber = docstring.length + 1;
  const lines = textContent.split('\n');

  const parsedLines: ParsedLine[] = provisions
    ? provisionsToParseLines(provisions)
    : lines.map((line, i) => {
        const match = line.match(/^(\s*)(.*)/);
        const indent = match?.[1] ?? '';
        const text = match?.[2] ?? line;
        return {
          lineIndex: i,
          indent,
          text,
          isListItem: /^\([a-zA-Z0-9]+\)/.test(text),
          isHeader: isHeaderLine(text),
        };
      });

  const tree = buildSections(parsedLines);

  function renderLineContent(pl: ParsedLine) {
    return (
      <>
        <span className="w-10 shrink-0 select-none text-right text-gray-400">
          {pl.lineIndex + 1 + blankLineNumber}
        </span>
        <span className="mx-2 select-none text-gray-400">│</span>
        {pl.indent && (
          <span className="shrink-0 whitespace-pre text-gray-800">
            {pl.indent}
          </span>
        )}
        <span
          className={`min-w-0 whitespace-pre-wrap ${pl.isHeader ? '' : 'text-gray-800'}${pl.isListItem ? ' pl-[4ch] -indent-[4ch]' : ''}`}
        >
          {pl.isHeader
            ? (() => {
                const headerMatch = pl.text.match(/^(\([a-zA-Z0-9]+\)\s*)(.*)/);
                const marker = headerMatch?.[1] ?? '';
                const title = headerMatch?.[2] ?? pl.text;
                return (
                  <>
                    <span className={headerMarkerClass}>{marker}</span>
                    <span className={headerTitleClass}>{title}</span>
                  </>
                );
              })()
            : pl.text}
        </span>
      </>
    );
  }

  // Whether we have real pixel measurements (false in jsdom / SSR).
  const hasMeasuredHeights = Array.from(headerHeights.values()).some(
    (h) => h > 0
  );

  function renderNode(
    node: TreeNode,
    parentTopPx: number = 0
  ): React.ReactNode {
    if (isSection(node)) {
      const pl = node.header;
      const measuredH = headerHeights.get(pl.lineIndex) ?? 0;
      // Parent headers need higher z-index so they render above child
      // headers during sticky transitions (prevents visual gap when a
      // child header unsticks and scrolls past its parent).
      const zIndex = 20 - node.depth;

      // Use measured pixel offsets when available; fall back to em
      // estimates (one line-height per depth level) in jsdom / SSR.
      // Offset depth-0 headers 1px above the scroll edge to seal
      // any sub-pixel gap between the header and the container top.
      const topPx = node.depth === 0 ? parentTopPx - 1 : parentTopPx;
      const topStyle = hasMeasuredHeights
        ? `${topPx}px`
        : `${node.depth * 1.625}em`;
      const childTopPx = parentTopPx + measuredH;

      return (
        <div key={`section-${pl.lineIndex}`}>
          <div
            ref={(el) => {
              if (el) headerRefs.current.set(pl.lineIndex, el);
              else headerRefs.current.delete(pl.lineIndex);
            }}
            data-sticky-header={pl.lineIndex}
            className="relative sticky flex items-start bg-gray-100"
            style={{
              top: topStyle,
              zIndex,
              paddingBottom: 4,
              marginBottom: -4,
            }}
          >
            {/* Extend background above/below header to occlude content
                scrolling behind, without negative marginTop that clips
                the preceding line's line numbers. */}
            <div
              className="pointer-events-none absolute inset-x-0 bg-gray-100"
              style={{
                top: node.depth === 0 ? -4 : -1,
                height: node.depth === 0 ? 4 : 1,
              }}
            />
            {renderLineContent(pl)}
          </div>
          {node.children.map((child) => renderNode(child, childTopPx))}
        </div>
      );
    }
    return (
      <div key={node.lineIndex} className="flex items-start">
        {renderLineContent(node)}
      </div>
    );
  }

  return (
    <div>
      <div
        ref={containerRef}
        className="rounded bg-gray-100 py-2 pr-8 font-mono text-sm leading-relaxed"
      >
        {docstring.map((text, i) => (
          <div key={`doc-${i}`} className="flex items-start text-green-700">
            <span className="w-10 shrink-0 select-none text-right text-gray-400">
              {i + 1}
            </span>
            <span className="mx-2 select-none text-gray-400">│</span>
            <span className="min-w-0 pl-[2ch] -indent-[2ch]">
              <span className="select-none"># </span>
              {text}
            </span>
          </div>
        ))}
        <div className="flex">
          <span className="w-10 shrink-0 select-none text-right text-gray-400">
            {blankLineNumber}
          </span>
          <span className="mx-2 select-none text-gray-400">│</span>
        </div>
        {tree.map(renderNode)}
      </div>
    </div>
  );
}
