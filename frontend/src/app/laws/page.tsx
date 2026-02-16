'use client';

import Link from 'next/link';
import { useLaws } from '@/hooks/useLaw';
import PageHeader from '@/components/ui/PageHeader';

export default function LawsPage() {
  const { data: laws, isLoading, error } = useLaws();

  if (isLoading) return <p className="text-gray-500">Loading laws...</p>;
  if (error || !laws)
    return <p className="text-red-600">Failed to load laws.</p>;

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
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                PL ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Title
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Enacted
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Sections Affected
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {laws.map((law) => (
              <tr
                key={`${law.congress}-${law.law_number}`}
                className="hover:bg-gray-50"
              >
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
                <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                  {law.enacted_date}
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
