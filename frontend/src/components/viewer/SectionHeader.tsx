import Link from 'next/link';
import type { BreadcrumbSegment, ItemStatus } from '@/lib/types';
import { statusBadge } from '@/lib/statusStyles';
import PageHeader from '@/components/ui/PageHeader';

/** A law reference for the enacted/amended lines. */
export interface LawReference {
  congress: number;
  date: string | null;
  label: string; // e.g. "PL 113-22"
  shortTitle?: string | null;
}

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

function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function formatDate(raw: string): string {
  // Backend may send ISO (YYYY-MM-DD) or prose ("Oct. 19, 1976") format
  const iso = /^\d{4}-\d{2}-\d{2}$/.test(raw);
  const date = new Date(iso ? raw + 'T00:00:00' : raw);
  if (isNaN(date.getTime())) return raw; // fallback to raw string
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}.${m}.${d}`;
}

function LawLine({ label, law }: { label: string; law: LawReference }) {
  return (
    <>
      <dt className="text-gray-400">{label}</dt>
      <dd className="text-gray-600">{ordinal(law.congress)} Congress</dd>
      <dd className="text-gray-600">{law.date ? formatDate(law.date) : '—'}</dd>
      <dd className="font-mono text-gray-600">{law.label}</dd>
      {law.shortTitle ? (
        <dd className="text-gray-500">{law.shortTitle}</dd>
      ) : (
        <dd />
      )}
    </>
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
