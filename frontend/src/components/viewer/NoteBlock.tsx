import type { SectionNote, CodeLine } from '@/lib/types';

interface NoteBlockProps {
  note: SectionNote;
  lineNumberOffset?: number;
}

/** Renders a single comment-styled line with line number and # prefix. */
function CommentLine({
  lineNumber,
  line,
}: {
  lineNumber: number;
  line: CodeLine;
}) {
  const indent = '\u00a0'.repeat(line.indent_level * 4);
  return (
    <div className="flex font-mono text-sm leading-relaxed text-green-700">
      <span className="w-10 shrink-0 select-none text-right text-gray-400">
        {lineNumber}
      </span>
      <span className="mx-2 select-none text-gray-400">│</span>
      <span>
        <span className="select-none"># </span>
        {indent}
        {line.is_header ? (
          <span className="font-semibold">{line.content}</span>
        ) : (
          line.content
        )}
      </span>
    </div>
  );
}

/** Renders a single structured note as a comment block with line numbers. */
export default function NoteBlock({
  note,
  lineNumberOffset = 1,
}: NoteBlockProps) {
  if (note.lines.length > 0) {
    return (
      <div className="mb-2">
        {note.lines.map((line, i) => (
          <CommentLine
            key={line.line_number}
            lineNumber={lineNumberOffset + i}
            line={line}
          />
        ))}
      </div>
    );
  }

  // Fallback: split content into lines and render each as a comment
  const contentLines = note.content.split('\n');
  return (
    <div className="mb-2">
      {contentLines.map((text, i) => (
        <CommentLine
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
