'use client';

import { useState } from 'react';
import { useSection } from '@/hooks/useSection';
import type { BreadcrumbSegment } from '@/lib/types';
import TabBar from '@/components/ui/TabBar';
import SectionHeader from './SectionHeader';
import SectionProvisions from './SectionProvisions';
import AmendmentList from './AmendmentList';
import CitationList from './CitationList';

interface SectionViewerProps {
  titleNumber: number;
  sectionNumber: string;
  breadcrumbs?: BreadcrumbSegment[];
}

const TABS = [
  { id: 'code', label: 'Code' },
  { id: 'history', label: 'History' },
];

/** Client component that fetches and renders section provisions. */
export default function SectionViewer({
  titleNumber,
  sectionNumber,
  breadcrumbs,
}: SectionViewerProps) {
  const { data, isLoading, error } = useSection(titleNumber, sectionNumber);
  const [activeTab, setActiveTab] = useState('code');

  if (isLoading) {
    return <p className="text-gray-500">Loading section...</p>;
  }

  if (error || !data) {
    return <p className="text-red-600">Failed to load section.</p>;
  }

  const amendments = data.notes?.amendments ?? [];
  const citations = data.notes?.citations ?? [];
  const hasHistory = amendments.length > 0 || citations.length > 0;

  const sorted = [...amendments].sort((a, b) => b.year - a.year);
  const latestAmendment =
    sorted.length > 0
      ? { publicLawId: sorted[0].public_law_id, year: sorted[0].year }
      : null;

  return (
    <div>
      <SectionHeader
        heading={data.heading}
        breadcrumbs={breadcrumbs}
        enactedDate={data.enacted_date}
        lastModifiedDate={data.last_modified_date}
        isPositiveLaw={data.is_positive_law}
        isRepealed={data.is_repealed}
        latestAmendment={latestAmendment}
      />
      {hasHistory && (
        <TabBar tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      )}
      {activeTab === 'code' ? (
        <SectionProvisions
          fullCitation={data.full_citation}
          heading={data.heading}
          textContent={data.text_content}
          provisions={data.provisions}
          isRepealed={data.is_repealed}
        />
      ) : (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <AmendmentList amendments={amendments} />
          <CitationList citations={citations} />
        </div>
      )}
    </div>
  );
}
