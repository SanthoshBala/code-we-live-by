import Link from 'next/link';
import type { SectionNote, CodeLine } from '@/lib/types';
import { findNoteLinks, type CrossRefLookup } from '@/lib/noteUtils';

interface NoteBlockProps {
  note: SectionNote;
  lineNumberOffset?: number;
  crossRefs?: CrossRefLookup;
  basePath?: string;
}

/**
 * Render line content, hyperlinking any cross-references to other note files.
 * Returns a plain string when there are no cross-refs to avoid unnecessary JSX.
 */
function renderContent(
  content: string,
  note: SectionNote,
  crossRefs: CrossRefLookup | undefined,
  basePath: string | undefined
) {
  if (!crossRefs || !basePath || crossRefs.size === 0) return content;

  const segments = findNoteLinks(content, crossRefs, note.category, basePath);
  if (segments.length === 0) return content;

  const nodes: any[] = [];
  let pos = 0;
  for (const seg of segments) {
    if (seg.start > pos) nodes.push(content.slice(pos, seg.start));
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
  if (pos < content.length) nodes.push(content.slice(pos));
  return <>{nodes}</>;
}

/** Renders a single line with line number and optional indent. */
function NoteLine({
  lineNumber,
  line,
  note,
  crossRefs,
  basePath,
}: {
  lineNumber: number;
  line: CodeLine;
  note: SectionNote;
  crossRefs?: CrossRefLookup;
  basePath?: string;
}) {
  const indent = line.indent_level > 0 ? '\t'.repeat(line.indent_level) : '';
  const isListItem = line.marker !== null;
  return (
    <div className="flex items-start font-mono text-sm leading-relaxed">
      <span className="w-10 shrink-0 select-none text-right text-gray-400">
        {lineNumber}
      </span>
      <span className="mx-2 select-none text-gray-400">|</span>
      {indent && (
        <span className="shrink-0 whitespace-pre text-gray-800">{indent}</span>
      )}
      <span
        className={`min-w-0 whitespace-pre-wrap text-gray-800${isListItem ? ' pl-[4ch] -indent-[4ch]' : ''}`}
      >
        {line.is_header ? (
          <span className="font-semibold">
            {renderContent(line.content, note, crossRefs, basePath)}
          </span>
        ) : (
          renderContent(line.content, note, crossRefs, basePath)
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
        />
      ))}
    </div>
  );
}
