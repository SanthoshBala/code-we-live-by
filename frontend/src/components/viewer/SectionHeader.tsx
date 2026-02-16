import Link from 'next/link';
import type { BreadcrumbSegment } from '@/lib/types';
import PageHeader from '@/components/ui/PageHeader';

interface SectionHeaderProps {
  heading: string;
  breadcrumbs?: BreadcrumbSegment[];
  enactedDate: string | null;
  lastModifiedDate: string | null;
  isPositiveLaw: boolean;
  isRepealed: boolean;
  latestAmendment?: { publicLawId: string; year: number } | null;
}

function Breadcrumbs({ segments }: { segments: BreadcrumbSegment[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mt-1 text-lg text-gray-600">
      {segments.map((seg, i) => (
        <span key={i}>
          {i > 0 && <span className="mx-1">/</span>}
          {seg.href ? (
            <Link href={seg.href} className="hover:text-primary-700">
              {seg.label}
            </Link>
          ) : (
            seg.label
          )}
        </span>
      ))}
    </nav>
  );
}

/** Renders the section heading, breadcrumbs, and metadata badges. */
export default function SectionHeader({
  heading,
  breadcrumbs,
  enactedDate,
  lastModifiedDate,
  isPositiveLaw,
  isRepealed,
  latestAmendment,
}: SectionHeaderProps) {
  return (
    <PageHeader
      title={heading}
      subtitle={
        breadcrumbs && breadcrumbs.length > 0 ? (
          <Breadcrumbs segments={breadcrumbs} />
        ) : undefined
      }
      badges={
        <>
          {isRepealed && (
            <span className="rounded-full bg-red-100 px-2.5 py-0.5 font-medium text-red-700">
              Repealed
            </span>
          )}
          {isPositiveLaw && (
            <span className="rounded-full bg-green-100 px-2.5 py-0.5 font-medium text-green-700">
              Positive Law
            </span>
          )}
          {enactedDate && (
            <span className="text-gray-500">Enacted {enactedDate}</span>
          )}
          {lastModifiedDate && (
            <span className="text-gray-500">
              Last modified {lastModifiedDate}
            </span>
          )}
          {latestAmendment && (
            <span className="rounded bg-primary-50 px-2 py-0.5 font-medium text-primary-700">
              Last amended by{' '}
              <span className="font-mono">{latestAmendment.publicLawId}</span> (
              {latestAmendment.year})
            </span>
          )}
        </>
      }
    />
  );
}
