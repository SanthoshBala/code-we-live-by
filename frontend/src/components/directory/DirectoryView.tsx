'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { DirectoryItem, BreadcrumbSegment } from '@/lib/types';
import PageHeader from '@/components/ui/PageHeader';
import TabBar from '@/components/ui/TabBar';
import DirectoryTable from './DirectoryTable';

interface DirectoryViewProps {
  title: string;
  breadcrumbs?: BreadcrumbSegment[];
  items: DirectoryItem[];
  revisionLabel?: string | null;
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

/** Directory explorer combining header, tab bar, and item table. */
export default function DirectoryView({
  title,
  breadcrumbs,
  items,
  revisionLabel: revLabel,
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
          revLabel ? (
            <span className="text-gray-500">Current through: {revLabel}</span>
          ) : undefined
        }
      />
      <TabBar tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      {activeTab === 'code' && <DirectoryTable items={items} />}
    </div>
  );
}
