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

/** Groups section notes by category and renders them in collapsible sections. */
export default function SectionNotes({ notes }: SectionNotesProps) {
  if (notes.length === 0) return null;

  const grouped = CATEGORY_ORDER.map((category) => ({
    category,
    label: CATEGORY_LABELS[category],
    items: notes.filter((n) => n.category === category),
  })).filter((g) => g.items.length > 0);

  return (
    <section className="mt-8">
      <h3 className="mb-4 text-lg font-semibold text-gray-900">Notes</h3>
      {grouped.map((group) => (
        <details key={group.category} open className="mb-4">
          <summary className="cursor-pointer text-sm font-medium text-gray-700">
            {group.label} ({group.items.length})
          </summary>
          <div className="mt-2 pl-4">
            {group.items.map((note, i) => (
              <NoteBlock key={i} note={note} />
            ))}
          </div>
        </details>
      ))}
    </section>
  );
}
