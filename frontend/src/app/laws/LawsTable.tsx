'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { formatLawDate } from '@/components/ui/LawLine';
import PageHeader from '@/components/ui/PageHeader';
import { fetchLawMeta } from '@/lib/api';
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
      {dir === 'asc' ? '▲' : '▼'}
    </span>
  );
}

const columns: { key: SortKey; label: string; align: string }[] = [
  { key: 'enacted_date', label: 'Enacted', align: 'text-left' },
  { key: 'pl_id', label: 'PL ID', align: 'text-left' },
  { key: 'title', label: 'Title', align: 'text-left' },
  { key: 'sections_affected', label: 'Sections Affected', align: 'text-right' },
];

interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  limit: number;
}

function Pagination({ page, totalPages, total, limit }: PaginationProps) {
  if (totalPages <= 1) return null;

  const start = (page - 1) * limit + 1;
  const end = Math.min(page * limit, total);

  // Show at most 5 page numbers centered around the current page
  const pageNumbers: number[] = [];
  const half = 2;
  let lo = Math.max(1, page - half);
  const hi = Math.min(totalPages, lo + 4);
  lo = Math.max(1, hi - 4);
  for (let i = lo; i <= hi; i++) pageNumbers.push(i);

  return (
    <div className="mt-4 flex items-center justify-between">
      <p className="text-sm text-gray-500">
        Showing {start}–{end} of {total} laws
      </p>
      <nav className="flex items-center gap-1" aria-label="Pagination">
        <Link
          href={`/laws?page=${page - 1}`}
          aria-disabled={page === 1}
          className={`rounded px-2 py-1 text-sm ${
            page === 1
              ? 'pointer-events-none text-gray-300'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          ← Prev
        </Link>
        {lo > 1 && (
          <>
            <Link
              href="/laws?page=1"
              className="rounded px-2 py-1 text-sm text-gray-600 hover:bg-gray-100"
            >
              1
            </Link>
            {lo > 2 && <span className="px-1 text-sm text-gray-400">…</span>}
          </>
        )}
        {pageNumbers.map((n) => (
          <Link
            key={n}
            href={`/laws?page=${n}`}
            className={`rounded px-2 py-1 text-sm ${
              n === page
                ? 'bg-primary-600 font-medium text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            {n}
          </Link>
        ))}
        {hi < totalPages && (
          <>
            {hi < totalPages - 1 && (
              <span className="px-1 text-sm text-gray-400">…</span>
            )}
            <Link
              href={`/laws?page=${totalPages}`}
              className="rounded px-2 py-1 text-sm text-gray-600 hover:bg-gray-100"
            >
              {totalPages}
            </Link>
          </>
        )}
        <Link
          href={`/laws?page=${page + 1}`}
          aria-disabled={page === totalPages}
          className={`rounded px-2 py-1 text-sm ${
            page === totalPages
              ? 'pointer-events-none text-gray-300'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          Next →
        </Link>
      </nav>
    </div>
  );
}

interface LawsTableProps {
  laws: LawSummary[];
  total: number;
  page: number;
  limit: number;
}

/** Sortable laws table. Receives a single page of data from the parent Server Component. */
export default function LawsTable({
  laws,
  total,
  page,
  limit,
}: LawsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('enacted_date');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const queryClient = useQueryClient();

  const totalPages = Math.max(1, Math.ceil(total / limit));

  const sorted = useMemo(() => {
    const copy = [...laws];
    copy.sort((a, b) => {
      let cmp = compareLaws(a, b, sortKey);
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
                    onMouseEnter={() => {
                      queryClient.prefetchQuery({
                        queryKey: ['lawMeta', law.congress, law.law_number],
                        queryFn: () =>
                          fetchLawMeta(law.congress, law.law_number),
                        staleTime: 5 * 60 * 1000,
                      });
                    }}
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

      <Pagination
        page={page}
        totalPages={totalPages}
        total={total}
        limit={limit}
      />
    </div>
  );
}
