import type { SectionNote } from '@/lib/types';
import NoteBlock from './NoteBlock';

interface SectionNotesProps {
  notes: SectionNote[];
}

const CATEGORY_LABELS: Record<SectionNote['category'], string> = {
  editorial: 'Editorial Notes',
  statutory: 'Statutory Notes',
  historical: 'Historical Notes',
};

const CATEGORY_ORDER: SectionNote['category'][] = [
  'editorial',
  'statutory',
  'historical',
];

/** Count lines a note will render. */
function noteLineCount(note: SectionNote): number {
  // +1 for the header line rendered by the category group
  if (note.lines.length > 0) return note.lines.length;
  return note.content.split('\n').length;
}

/** Groups section notes by category and renders them as comment blocks. */
export default function SectionNotes({ notes }: SectionNotesProps) {
  if (notes.length === 0) return null;

  const grouped = CATEGORY_ORDER.map((category) => ({
    category,
    label: CATEGORY_LABELS[category],
    items: notes.filter((n) => n.category === category),
  })).filter((g) => g.items.length > 0);

  return (
    <section className="mt-8">
      {grouped.map((group) => {
        let lineNumber = 1;

        return (
          <details key={group.category} open className="mb-6">
            <summary className="cursor-pointer text-sm font-medium text-gray-700">
              {group.label} ({group.items.length})
            </summary>
            <div className="mt-2 rounded bg-gray-50 py-2">
              {group.items.map((note, i) => {
                // Render the note header as a comment header line
                const headerLineNum = lineNumber;
                lineNumber += 1;
                const contentOffset = lineNumber;
                lineNumber += noteLineCount(note);

                return (
                  <div key={i}>
                    <div className="flex font-mono text-sm leading-relaxed text-green-700">
                      <span className="w-10 shrink-0 select-none text-right text-gray-400">
                        {headerLineNum}
                      </span>
                      <span className="mx-2 select-none text-gray-400">│</span>
                      <span>
                        <span className="select-none"># </span>
                        <span className="font-semibold">{note.header}</span>
                      </span>
                    </div>
                    <NoteBlock note={note} lineNumberOffset={contentOffset} />
                  </div>
                );
              })}
            </div>
          </details>
        );
      })}
    </section>
  );
}
