'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { fetchRevision } from '@/lib/api';
import { revisionLabel } from '@/lib/revisionLabel';

interface RevisionBannerProps {
  revision: number;
}

/**
 * Banner displayed when viewing the code at a non-HEAD revision.
 * Shows revision metadata and a link to return to the latest version.
 */
export default function RevisionBanner({ revision }: RevisionBannerProps) {
  const pathname = usePathname();
  const { data } = useQuery({
    queryKey: ['revision', revision],
    queryFn: () => fetchRevision(revision),
    staleTime: Infinity,
  });

  const label = data ? revisionLabel(data) : `Revision ${revision}`;

  return (
    <div className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <span>
          Viewing as of <strong>{label}</strong>
        </span>
        <Link
          href={pathname}
          className="font-medium text-amber-700 underline hover:text-amber-900"
        >
          View latest
        </Link>
      </div>
    </div>
  );
}
