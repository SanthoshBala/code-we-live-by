'use client';

import { useState, useTransition, useRef } from 'react';
import Link from 'next/link';
import { searchSections, searchLaws } from '@/lib/api';
import type { SectionSearchResult, LawSearchResult } from '@/lib/types';

type Tab = 'sections' | 'laws';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [activeTab, setActiveTab] = useState<Tab>('sections');
  const [sectionResults, setSectionResults] = useState<SectionSearchResult[]>(
    []
  );
  const [lawResults, setLawResults] = useState<LawSearchResult[]>([]);
  const [sectionTotal, setSectionTotal] = useState(0);
  const [lawTotal, setLawTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (q.length < 2) return;
    setError(null);

    startTransition(async () => {
      try {
        const [sec, law] = await Promise.all([
          searchSections(q, { limit: 20 }),
          searchLaws(q, { limit: 20 }),
        ]);
        setSectionResults(sec.results);
        setSectionTotal(sec.total);
        setLawResults(law.results);
        setLawTotal(law.total);
      } catch {
        setError('Search failed. Please try again.');
      }
    });
  }

  const hasResults = sectionResults.length > 0 || lawResults.length > 0;
  const searched =
    sectionTotal > 0 ||
    lawTotal > 0 ||
    (!isPending && query.trim().length >= 2);

  return (
    <main className="min-h-screen p-8">
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-2 text-3xl font-bold">Search</h1>
        <p className="mb-6 text-gray-600">
          Find sections of the US Code or Public Laws by keyword.
        </p>

        <form onSubmit={handleSearch} className="mb-8 flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. privacy, copyright, annual report…"
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
            minLength={2}
          />
          <button
            type="submit"
            disabled={isPending || query.trim().length < 2}
            className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
          >
            {isPending ? 'Searching…' : 'Search'}
          </button>
        </form>

        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

        {hasResults && (
          <>
            <div className="mb-4 flex gap-4 border-b border-gray-200">
              <button
                onClick={() => setActiveTab('sections')}
                className={`pb-2 text-sm font-medium transition-colors ${
                  activeTab === 'sections'
                    ? 'border-b-2 border-blue-600 text-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Sections ({sectionTotal})
              </button>
              <button
                onClick={() => setActiveTab('laws')}
                className={`pb-2 text-sm font-medium transition-colors ${
                  activeTab === 'laws'
                    ? 'border-b-2 border-blue-600 text-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Laws ({lawTotal})
              </button>
            </div>

            {activeTab === 'sections' && (
              <SectionResults results={sectionResults} total={sectionTotal} />
            )}
            {activeTab === 'laws' && (
              <LawResults results={lawResults} total={lawTotal} />
            )}
          </>
        )}

        {!hasResults && searched && !isPending && (
          <p className="text-sm text-gray-500">
            No results found for &ldquo;{query}&rdquo;.
          </p>
        )}
      </div>
    </main>
  );
}

function SectionResults({
  results,
  total,
}: {
  results: SectionSearchResult[];
  total: number;
}) {
  return (
    <div className="space-y-4">
      {total > results.length && (
        <p className="text-xs text-gray-500">
          Showing {results.length} of {total} results
        </p>
      )}
      {results.map((r) => (
        <div
          key={`${r.title_number}-${r.section_number}`}
          className="rounded-lg border border-gray-200 bg-white p-4"
        >
          <Link
            href={`/sections/${r.title_number}/${encodeURIComponent(r.section_number)}`}
            className="font-medium text-blue-700 hover:underline"
          >
            {r.full_citation}
          </Link>
          <p className="mt-0.5 text-sm text-gray-700">{r.heading}</p>
          {r.snippet && (
            <p className="mt-1 line-clamp-3 text-xs text-gray-500">
              {r.snippet}
            </p>
          )}
          {r.is_repealed && (
            <span className="mt-1 inline-block rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-700">
              Repealed
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function LawResults({
  results,
  total,
}: {
  results: LawSearchResult[];
  total: number;
}) {
  return (
    <div className="space-y-4">
      {total > results.length && (
        <p className="text-xs text-gray-500">
          Showing {results.length} of {total} results
        </p>
      )}
      {results.map((r) => (
        <div
          key={`${r.congress}-${r.law_number}`}
          className="rounded-lg border border-gray-200 bg-white p-4"
        >
          <Link
            href={`/laws/${r.congress}/${encodeURIComponent(r.law_number)}`}
            className="font-medium text-blue-700 hover:underline"
          >
            PL {r.congress}-{r.law_number}
          </Link>
          {(r.short_title || r.popular_name) && (
            <p className="mt-0.5 text-sm text-gray-700">
              {r.short_title ?? r.popular_name}
            </p>
          )}
          {r.enacted_date && (
            <p className="mt-1 text-xs text-gray-500">
              Enacted {r.enacted_date}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
