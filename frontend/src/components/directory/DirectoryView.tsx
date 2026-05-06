'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type {
  DirectoryItem,
  BreadcrumbSegment,
  HeadRevision,
} from '@/lib/types';
import PageHeader from '@/components/ui/PageHeader';
import TabBar from '@/components/ui/TabBar';
import DirectoryTable from './DirectoryTable';

interface DirectoryViewProps {
  title: string;
  breadcrumbs?: BreadcrumbSegment[];
  items: DirectoryItem[];
  revisionData?: HeadRevision | null;
  revision?: number;
}

const TABS = [{ id: 'code', label: 'Code' }];

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

/** Format a congress number with ordinal suffix (e.g. 113 → "113th Congress"). */
function congressLabel(congress: number): string {
  const suffixes: Record<number, string> = { 1: 'st', 2: 'nd', 3: 'rd' };
  const lastTwo = congress % 100;
  const suffix =
    lastTwo >= 11 && lastTwo <= 13 ? 'th' : (suffixes[congress % 10] ?? 'th');
  return `${congress}${suffix} Congress`;
}

/** Extract congress number from a revision summary like "OLRC release point 113-21". */
function extractCongress(summary: string | null): number | null {
  if (!summary) return null;
  const match = summary.match(/(\d+)-\d+/);
  return match ? Number(match[1]) : null;
}

/** Format the revision's display title (summary without the "Initial commit: " prefix). */
function displayTitle(summary: string | null, revisionType: string): string {
  if (!summary) {
    return revisionType === 'Release_Point' ? 'Release Point' : 'Public Law';
  }
  return summary.replace(/^Initial commit:\s*/i, '');
}

function formatDate(effectiveDate: string): string {
  const date = new Date(effectiveDate + 'T00:00:00');
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}.${m}.${d}`;
}

function RevisionBadge({
  data,
  revision,
}: {
  data: HeadRevision;
  revision?: number;
}) {
  const pathname = usePathname();
  const isHistorical = revision !== undefined;
  const congress = extractCongress(data.summary);
  const title = displayTitle(data.summary, data.revision_type);
  const date = formatDate(data.effective_date);

  return (
    <span
      className={`inline-flex w-full items-center justify-between rounded-lg px-4 py-1.5 text-sm ${
        isHistorical
          ? 'border border-amber-200 bg-amber-50 text-amber-900'
          : 'border border-gray-200 bg-gray-50 text-gray-700'
      }`}
    >
      <span className="flex items-center gap-1">
        {congress && (
          <>
            <span>{congressLabel(congress)}</span>
            <span className={isHistorical ? 'text-amber-300' : 'text-gray-300'}>
              ·
            </span>
          </>
        )}
        <span>{title}</span>
        <span className={isHistorical ? 'text-amber-300' : 'text-gray-300'}>
          ·
        </span>
        <span>{date}</span>
      </span>
      <span className="flex items-center gap-2">
        {isHistorical && (
          <>
            <Link
              href={pathname}
              className="text-sm font-medium text-amber-700 underline hover:text-amber-900"
            >
              View latest
            </Link>
            <span className="text-amber-300">·</span>
          </>
        )}
        <Link
          href="/revisions"
          className={`text-sm font-medium underline ${
            isHistorical
              ? 'text-amber-700 hover:text-amber-900'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          History
        </Link>
      </span>
    </span>
  );
}

/** Directory explorer combining header, tab bar, and item table. */
export default function DirectoryView({
  title,
  breadcrumbs,
  items,
  revisionData,
  revision,
}: DirectoryViewProps) {
  const [activeTab, setActiveTab] = useState('code');

  return (
    <div>
      <PageHeader
        title={title}
        subtitle={
          breadcrumbs && breadcrumbs.length > 0 ? (
            <Breadcrumbs segments={breadcrumbs} />
          ) : undefined
        }
        badges={
          revisionData ? (
            <RevisionBadge data={revisionData} revision={revision} />
          ) : undefined
        }
      />
      <TabBar tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      {activeTab === 'code' && <DirectoryTable items={items} />}
    </div>
  );
}
