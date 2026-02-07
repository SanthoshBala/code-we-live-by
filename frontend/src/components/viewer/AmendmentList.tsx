import type { Amendment } from '@/lib/types';

interface AmendmentListProps {
  amendments: Amendment[];
}

/** Renders amendment history grouped by year, newest first. */
export default function AmendmentList({ amendments }: AmendmentListProps) {
  if (amendments.length === 0) return null;

  const sorted = [...amendments].sort((a, b) => b.year - a.year);

  const grouped: { year: number; items: Amendment[] }[] = [];
  for (const amendment of sorted) {
    const last = grouped[grouped.length - 1];
    if (last && last.year === amendment.year) {
      last.items.push(amendment);
    } else {
      grouped.push({ year: amendment.year, items: [amendment] });
    }
  }

  return (
    <section className="mt-8">
      <h3 className="mb-4 text-lg font-semibold text-gray-900">
        Amendment History
      </h3>
      {grouped.map((group) => (
        <div key={group.year} className="mb-4">
          <h4 className="mb-1 text-sm font-semibold text-gray-700">
            {group.year}
          </h4>
          <ul className="space-y-1 pl-4">
            {group.items.map((a, i) => (
              <li key={i} className="text-sm text-gray-600">
                <span className="font-mono text-xs text-gray-500">
                  {a.public_law_id}
                </span>
                {a.description && <span className="ml-2">{a.description}</span>}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
