import Link from 'next/link';
import type { BreadcrumbSegment, ItemStatus } from '@/lib/types';
import { statusBadge } from '@/lib/statusStyles';
import PageHeader from '@/components/ui/PageHeader';
import LawLine from '@/components/ui/LawLine';
export type { LawReference } from '@/components/ui/LawLine';
import type { LawReference } from '@/components/ui/LawLine';

interface SectionHeaderProps {
  heading: string;
  breadcrumbs?: BreadcrumbSegment[];
  isPositiveLaw: boolean;
  status: ItemStatus;
  enacted?: LawReference | null;
  lastAmended?: LawReference | null;
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
  isPositiveLaw,
  status,
  enacted,
  lastAmended,
}: SectionHeaderProps) {
  const badge = statusBadge(status);
  const hasLawInfo = enacted || lastAmended;

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
          {badge && (
            <span
              className={`rounded-full px-2.5 py-0.5 font-medium ${badge.className}`}
            >
              {badge.label}
            </span>
          )}
          {isPositiveLaw && (
            <span className="rounded-full bg-green-100 px-2.5 py-0.5 font-medium text-green-700">
              Positive Law
            </span>
          )}
          {hasLawInfo && (
            <dl className="grid grid-cols-[auto_auto_auto_auto_auto] gap-x-3 gap-y-0.5">
              {enacted && <LawLine label="Enacted:" law={enacted} />}
              {lastAmended && (
                <LawLine label="Last amended:" law={lastAmended} />
              )}
            </dl>
          )}
        </>
      }
    />
  );
}
