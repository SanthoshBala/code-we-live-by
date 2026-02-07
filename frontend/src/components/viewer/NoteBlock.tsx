import type { SectionNote } from '@/lib/types';

interface NoteBlockProps {
  note: SectionNote;
}

/** Renders a single structured note with its header and indented lines. */
export default function NoteBlock({ note }: NoteBlockProps) {
  return (
    <div className="mb-4">
      <h4 className="mb-1 text-sm font-semibold text-gray-700">
        {note.header}
      </h4>
      {note.lines.length > 0 ? (
        <div className="text-sm leading-relaxed text-gray-600">
          {note.lines.map((line) => (
            <div
              key={line.line_number}
              style={{ paddingLeft: `${line.indent_level}rem` }}
            >
              {line.content}
            </div>
          ))}
        </div>
      ) : (
        <pre className="whitespace-pre-wrap text-sm leading-relaxed text-gray-600">
          {note.content}
        </pre>
      )}
    </div>
  );
}
