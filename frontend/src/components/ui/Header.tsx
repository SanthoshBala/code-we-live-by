'use client';

import Link from 'next/link';
import { useHeadRevision } from '@/hooks/useHeadRevision';
import { formatRevisionLabel } from '@/lib/revisionLabel';

export default function Header() {
  const { data: revision } = useHeadRevision();

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="text-xl font-bold text-primary-700">
          The Code We Live By
        </Link>
        <nav className="flex items-center gap-4">
          {revision && (
            <span className="hidden text-xs text-gray-400 sm:inline">
              Current through:{' '}
              {formatRevisionLabel(
                revision.revision_type,
                revision.summary,
                revision.effective_date
              )}
            </span>
          )}
          <Link
            href="/titles"
            className="text-sm font-medium text-gray-600 hover:text-primary-600"
          >
            Browse Titles
          </Link>
          <Link
            href="/laws"
            className="text-sm font-medium text-gray-600 hover:text-primary-600"
          >
            Laws
          </Link>
        </nav>
      </div>
    </header>
  );
}
