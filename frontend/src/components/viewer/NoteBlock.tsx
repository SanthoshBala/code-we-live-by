import type { SectionNote, CodeLine } from '@/lib/types';

interface NoteBlockProps {
  note: SectionNote;
  lineNumberOffset?: number;
}

/** Renders a single line with line number and optional indent. */
function NoteLine({
  lineNumber,
  line,
}: {
  lineNumber: number;
  line: CodeLine;
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
          <span className="font-semibold">{line.content}</span>
        ) : (
          line.content
        )}
      </span>
    </div>
  );
}

/** Renders a single structured note as a block with line numbers. */
export default function NoteBlock({
  note,
  lineNumberOffset = 1,
}: NoteBlockProps) {
  if (note.lines.length > 0) {
    return (
      <div className="mb-2">
        {note.lines.map((line, i) => (
          <NoteLine
            key={line.line_number}
            lineNumber={lineNumberOffset + i}
            line={line}
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
        />
      ))}
    </div>
  );
}
