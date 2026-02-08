import type { SectionNote } from '@/lib/types';
import NoteBlock from './NoteBlock';

interface SectionNotesProps {
  notes: SectionNote[];
  fullCitation: string;
  heading: string;
  categoryLabel: string;
}

/** Count lines a note will render. */
function noteLineCount(note: SectionNote): number {
  if (note.lines.length > 0) return note.lines.length;
  return note.content.split('\n').length;
}

/** Renders section notes as numbered lines in a code-style block. */
export default function SectionNotes({
  notes,
  fullCitation,
  heading,
  categoryLabel,
}: SectionNotesProps) {
  if (notes.length === 0) return null;

  const docstring = [fullCitation, heading, categoryLabel];
  const blankLineNumber = docstring.length + 1;
  let lineNumber = blankLineNumber + 1;

  return (
    <div className="rounded bg-gray-100 py-2 pr-8 font-mono text-sm leading-relaxed">
      {docstring.map((text, i) => (
        <div key={`doc-${i}`} className="flex items-start text-green-700">
          <span className="w-10 shrink-0 select-none text-right text-gray-400">
            {i + 1}
          </span>
          <span className="mx-2 select-none text-gray-400">|</span>
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
        <span className="mx-2 select-none text-gray-400">|</span>
      </div>
      {notes.map((note, i) => {
        const headerLineNum = lineNumber;
        lineNumber += 1;
        const contentOffset = lineNumber;
        lineNumber += noteLineCount(note);

        return (
          <div key={i}>
            <div className="flex">
              <span className="w-10 shrink-0 select-none text-right text-gray-400">
                {headerLineNum}
              </span>
              <span className="mx-2 select-none text-gray-400">|</span>
              <span className="font-semibold text-gray-900">{note.header}</span>
            </div>
            <NoteBlock note={note} lineNumberOffset={contentOffset} />
          </div>
        );
      })}
    </div>
  );
}
