import type { ReactNode } from 'react';
import Link from 'next/link';
import type { SectionNote, CodeLine } from '@/lib/types';
import { findNoteLinks, type CrossRefLookup } from '@/lib/noteUtils';
import { linkifyContent } from '@/lib/linkifyContent';

interface NoteBlockProps {
  note: SectionNote;
  lineNumberOffset?: number;
  crossRefs?: CrossRefLookup;
  basePath?: string;
  withRev?: (href: string) => string;
}

/**
 * Render line content with two layers of hyperlinking:
 * 1. USC/law references from note.references (via linkifyContent)
 * 2. Cross-references to other note categories (via findNoteLinks)
 */
function renderContent(
  content: string,
  note: SectionNote,
  crossRefs: CrossRefLookup | undefined,
  basePath: string | undefined,
  withRev: (href: string) => string = (h) => h
): ReactNode {
  const refs = note.references ?? [];
  const hasCrossRefs = crossRefs && basePath && crossRefs.size > 0;

  if (!hasCrossRefs && refs.length === 0) return content;

  if (!hasCrossRefs) {
    return linkifyContent(content, refs, withRev);
  }

  const segments = findNoteLinks(content, crossRefs, note.category, basePath);
  if (segments.length === 0) {
    return refs.length > 0 ? linkifyContent(content, refs, withRev) : content;
  }

  const nodes: ReactNode[] = [];
  let pos = 0;
  for (const seg of segments) {
    if (seg.start > pos) {
      const plain = content.slice(pos, seg.start);
      nodes.push(
        refs.length > 0 ? linkifyContent(plain, refs, withRev) : plain
      );
    }
    nodes.push(
      <Link
        key={seg.start}
        href={seg.url}
        className="text-blue-600 hover:underline"
      >
        {seg.text}
      </Link>
    );
    pos = seg.end;
  }
  if (pos < content.length) {
    const plain = content.slice(pos);
    nodes.push(refs.length > 0 ? linkifyContent(plain, refs, withRev) : plain);
  }
  return <>{nodes}</>;
}

/** Renders a single line with line number and optional indent. */
function NoteLine({
  lineNumber,
  line,
  note,
  crossRefs,
  basePath,
  withRev,
}: {
  lineNumber: number;
  line: CodeLine;
  note: SectionNote;
  crossRefs?: CrossRefLookup;
  basePath?: string;
  withRev?: (href: string) => string;
}) {
  const indent = line.indent_level > 0 ? '\t'.repeat(line.indent_level) : '';
  const isListItem = line.marker !== null;
  return (
    <div className="flex items-start font-mono text-sm leading-relaxed">
      <span className="w-10 shrink-0 select-none text-right text-gray-400">
        {lineNumber}
      </span>
      <span className="mx-2 select-none text-gray-400">│</span>
      {indent && (
        <span className="shrink-0 whitespace-pre text-gray-800">{indent}</span>
      )}
      <span
        className={`min-w-0 whitespace-pre-wrap text-gray-800${isListItem ? ' pl-[4ch] -indent-[4ch]' : ''}`}
      >
        {line.is_header ? (
          <span className="font-semibold">
            {renderContent(line.content, note, crossRefs, basePath, withRev)}
          </span>
        ) : (
          renderContent(line.content, note, crossRefs, basePath, withRev)
        )}
      </span>
    </div>
  );
}

/** Renders a single structured note as a block with line numbers. */
export default function NoteBlock({
  note,
  lineNumberOffset = 1,
  crossRefs,
  basePath,
  withRev,
}: NoteBlockProps) {
  if (note.lines.length > 0) {
    return (
      <div className="mb-2">
        {note.lines.map((line, i) => (
          <NoteLine
            key={line.line_number}
            lineNumber={lineNumberOffset + i}
            line={line}
            note={note}
            crossRefs={crossRefs}
            basePath={basePath}
            withRev={withRev}
          />
        ))}
      </div>
    );
  }

  // Fallback: split content into lines and render each
  const contentLines = note.content.split('\n');
  return (
    <div className="mb-2">
      {contentLines.map((text, i) => (
        <NoteLine
          key={i}
          lineNumber={lineNumberOffset + i}
          line={{
            line_number: i + 1,
            content: text,
            indent_level: 0,
            marker: null,
            is_header: false,
          }}
          note={note}
          crossRefs={crossRefs}
          basePath={basePath}
          withRev={withRev}
        />
      ))}
    </div>
  );
}
