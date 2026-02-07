import type { SourceLaw } from '@/lib/types';

interface CitationListProps {
  citations: SourceLaw[];
}

const RELATIONSHIP_COLORS: Record<string, string> = {
  Framework: 'bg-blue-100 text-blue-700',
  Enactment: 'bg-green-100 text-green-700',
  Amendment: 'bg-amber-100 text-amber-700',
};

/** Renders source law citations with relationship badges. */
export default function CitationList({ citations }: CitationListProps) {
  if (citations.length === 0) return null;

  return (
    <section className="mt-8">
      <h3 className="mb-4 text-lg font-semibold text-gray-900">
        Source Laws
      </h3>
      <ul className="space-y-2">
        {citations.map((c, i) => (
          <li key={i} className="text-sm text-gray-600">
            <span className="font-mono text-xs text-gray-500">{c.law_id}</span>
            <span
              className={`ml-2 rounded-full px-2 py-0.5 text-xs font-medium ${RELATIONSHIP_COLORS[c.relationship] ?? 'bg-gray-100 text-gray-600'}`}
            >
              {c.relationship}
            </span>
            {c.raw_text && (
              <span className="ml-2 text-gray-500">{c.raw_text}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
