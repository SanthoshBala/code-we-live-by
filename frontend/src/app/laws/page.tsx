'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useLaws } from '@/hooks/useLaw';
import { formatLawDate } from '@/components/ui/LawLine';
import PageHeader from '@/components/ui/PageHeader';
import type { LawSummary } from '@/lib/types';

type SortKey = 'enacted_date' | 'pl_id' | 'title' | 'sections_affected';
type SortDir = 'asc' | 'desc';

function compareLaws(a: LawSummary, b: LawSummary, key: SortKey): number {
  switch (key) {
    case 'enacted_date':
      return a.enacted_date.localeCompare(b.enacted_date);
    case 'pl_id': {
      const cmp = a.congress - b.congress;
      return cmp !== 0 ? cmp : Number(a.law_number) - Number(b.law_number);
    }
    case 'title': {
      const aTitle = (a.short_title || a.official_title || '').toLowerCase();
      const bTitle = (b.short_title || b.official_title || '').toLowerCase();
      return aTitle.localeCompare(bTitle);
    }
    case 'sections_affected':
      return a.sections_affected - b.sections_affected;
  }
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) {
    return <span className="ml-1 inline-block text-gray-300">&#8597;</span>;
  }
  return (
    <span className="ml-1 inline-block text-gray-600">
      {dir === 'asc' ? '\u25B2' : '\u25BC'}
    </span>
  );
}

export default function LawsPage() {
  const { data: laws, isLoading, error } = useLaws();
  const [sortKey, setSortKey] = useState<SortKey>('enacted_date');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const sorted = useMemo(() => {
    if (!laws) return [];
    const copy = [...laws];
    copy.sort((a, b) => {
      let cmp = compareLaws(a, b, sortKey);
      // Tiebreaker: enacted date then law number ascending
      if (cmp === 0 && sortKey !== 'enacted_date') {
        cmp = a.enacted_date.localeCompare(b.enacted_date);
      }
      if (cmp === 0 && sortKey !== 'pl_id') {
        cmp =
          a.congress - b.congress ||
          Number(a.law_number) - Number(b.law_number);
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return copy;
  }, [laws, sortKey, sortDir]);

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'sections_affected' ? 'desc' : 'asc');
    }
  }

  if (isLoading) return <p className="text-gray-500">Loading laws...</p>;
  if (error || !laws)
    return <p className="text-red-600">Failed to load laws.</p>;

  const columns: { key: SortKey; label: string; align: string }[] = [
    { key: 'enacted_date', label: 'Enacted', align: 'text-left' },
    { key: 'pl_id', label: 'PL ID', align: 'text-left' },
    { key: 'title', label: 'Title', align: 'text-left' },
    {
      key: 'sections_affected',
      label: 'Sections Affected',
      align: 'text-right',
    },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Public Laws"
        subtitle="Browse enacted legislation in the database"
      />

      <div className="mt-6 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`cursor-pointer select-none px-4 py-3 text-xs font-medium uppercase tracking-wider text-gray-500 hover:text-gray-700 ${col.align}`}
                  onClick={() => handleSort(col.key)}
                >
                  {col.label}
                  <SortIcon active={sortKey === col.key} dir={sortDir} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {sorted.map((law) => (
              <tr
                key={`${law.congress}-${law.law_number}`}
                className="hover:bg-gray-50"
              >
                <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                  {formatLawDate(law.enacted_date)}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm">
                  <Link
                    href={`/laws/${law.congress}/${law.law_number}`}
                    className="font-medium text-primary-600 hover:text-primary-700"
                  >
                    PL {law.congress}-{law.law_number}
                  </Link>
                </td>
                <td className="max-w-md truncate px-4 py-3 text-sm text-gray-700">
                  {law.short_title || law.official_title || '—'}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-500">
                  {law.sections_affected}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {laws.length === 0 && (
          <p className="py-8 text-center text-sm text-gray-500">
            No laws in the database yet.
          </p>
        )}
      </div>
    </div>
  );
}
