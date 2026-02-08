'use client';

import { useEffect, useRef, useState } from 'react';
import type { CodeLine } from '@/lib/types';

interface SectionProvisionsProps {
  fullCitation: string;
  heading: string;
  textContent: string | null;
  provisions: CodeLine[] | null;
  isRepealed: boolean;
}

// Legacy heuristic fallback — used when structured provisions are not available.
// Will be removed after all sections are re-ingested with normalized_provisions.
function isHeaderLine(text: string): boolean {
  if (!/^\([a-zA-Z0-9]+\)/.test(text)) return false;
  if (text.length > 80) return false;
  if (/[.;,:—]$/.test(text)) return false;
  if (/\b(or|and)$/.test(text)) return false;
  return true;
}

const headerMarkerClass = 'text-blue-600';
const headerTitleClass = 'font-bold text-blue-700';

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
  isRepealed,
}: SectionProvisionsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [stuckHeaders, setStuckHeaders] = useState<Set<number>>(new Set());

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof IntersectionObserver === 'undefined') return;

    setStuckHeaders(new Set());

    // Find the nearest scrollable ancestor for the IO root
    let scrollParent: Element | null = container.parentElement;
    while (scrollParent) {
      const { overflowY } = getComputedStyle(scrollParent);
      if (overflowY === 'auto' || overflowY === 'scroll') break;
      scrollParent = scrollParent.parentElement;
    }

    const sentinels = container.querySelectorAll<HTMLElement>(
      '[data-sticky-sentinel]'
    );

    const observer = new IntersectionObserver(
      (entries) => {
        setStuckHeaders((prev) => {
          const next = new Set(prev);
          for (const entry of entries) {
            const index = Number(
              (entry.target as HTMLElement).dataset.stickySentinel
            );
            if (
              !entry.isIntersecting &&
              entry.boundingClientRect.top < (entry.rootBounds?.top ?? 0)
            ) {
              next.add(index);
            } else {
              next.delete(index);
            }
          }
          return next;
        });
      },
      { root: scrollParent, threshold: 0 }
    );

    sentinels.forEach((s) => observer.observe(s));
    return () => observer.disconnect();
  }, [textContent]);

  if (!textContent) {
    return (
      <div className="rounded border border-gray-200 bg-gray-50 px-4 py-6 text-center text-sm text-gray-500">
        {isRepealed
          ? 'This section has been repealed.'
          : 'No text content available for this section.'}
      </div>
    );
  }

  const docstring = [fullCitation, heading];
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

  function renderNode(node: TreeNode): React.ReactNode {
    if (isSection(node)) {
      const pl = node.header;
      const topOffset = node.depth * 1.625;
      return (
        <div key={`section-${pl.lineIndex}`}>
          <div
            data-sticky-sentinel={pl.lineIndex}
            className="h-0"
            aria-hidden="true"
          />
          <div
            data-sticky-header={pl.lineIndex}
            className={`sticky z-10 flex items-start bg-gray-100${stuckHeaders.has(pl.lineIndex) ? ' border-b border-gray-200' : ''}`}
            style={{ top: `${topOffset}em` }}
          >
            {renderLineContent(pl)}
          </div>
          {node.children.map(renderNode)}
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
            <span className="min-w-0 pl-[4ch] -indent-[4ch]">
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
