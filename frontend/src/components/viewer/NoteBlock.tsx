import Link from 'next/link';
import type { ReactNode } from 'react';
import type { SectionNote, CodeLine, NoteReference } from '@/lib/types';
import { findNoteLinks, type CrossRefLookup } from '@/lib/noteUtils';
import { linkifyContent } from '@/lib/linkifyContent';

interface NoteBlockProps {
  note: SectionNote;
  lineNumberOffset?: number;
  crossRefs?: CrossRefLookup;
  basePath?: string;
  externalRefs?: NoteReference[];
}

const identity = (href: string) => href;

/**
 * Render line content, linking both cross-note refs and external law/section refs.
 *
 * Cross-note links (e.g. "Effective Date note below") take priority. External
 * refs (Public Laws, USC sections) are applied to the text gaps between them.
 */
function renderContent(
  content: string,
  note: SectionNote,
  crossRefs: CrossRefLookup | undefined,
  basePath: string | undefined,
  externalRefs: NoteReference[]
): ReactNode {
  const noteSegs =
    crossRefs && basePath && crossRefs.size > 0
      ? findNoteLinks(content, crossRefs, note.category, basePath)
      : [];

  const applyExternal = (text: string): ReactNode =>
    externalRefs.length > 0
      ? linkifyContent(text, externalRefs, identity)
      : text;

  if (noteSegs.length === 0) return applyExternal(content);

  const linkClass = 'text-blue-600 hover:underline';
  const parts: ReactNode[] = [];
  let cursor = 0;
  for (const seg of noteSegs) {
    if (seg.start > cursor) {
      parts.push(
        <span key={`t-${cursor}`}>
          {applyExternal(content.slice(cursor, seg.start))}
        </span>
      );
    }
    parts.push(
      <Link key={`n-${seg.start}`} href={seg.url} className={linkClass}>
        {seg.text}
      </Link>
    );
    cursor = seg.end;
  }
  if (cursor < content.length) {
    parts.push(
      <span key={`t-${cursor}`}>{applyExternal(content.slice(cursor))}</span>
    );
  }
  return <>{parts}</>;
}

/** Renders a single line with line number and optional indent. */
function NoteLine({
  lineNumber,
  line,
  note,
  crossRefs,
  basePath,
  externalRefs = [],
}: {
  lineNumber: number;
  line: CodeLine;
  note: SectionNote;
  crossRefs?: CrossRefLookup;
  basePath?: string;
  externalRefs?: NoteReference[];
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
            {renderContent(
              line.content,
              note,
              crossRefs,
              basePath,
              externalRefs
            )}
          </span>
        ) : (
          renderContent(line.content, note, crossRefs, basePath, externalRefs)
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
  externalRefs = [],
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
            externalRefs={externalRefs}
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
          externalRefs={externalRefs}
        />
      ))}
    </div>
  );
}
