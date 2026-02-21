'use client';

import { useState } from 'react';
import { useSection } from '@/hooks/useSection';
import type { BreadcrumbSegment } from '@/lib/types';
import TabBar from '@/components/ui/TabBar';
import SectionHeader from './SectionHeader';
import type { LawReference } from './SectionHeader';
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
  const shortTitles = data.notes?.short_titles ?? [];
  const hasHistory = amendments.length > 0 || citations.length > 0;

  // Helper: find the short title associated with a public law ID
  const findShortTitle = (plId: string): string | null =>
    shortTitles.find((st) => st.public_law === plId)?.title ?? null;

  // Build enacted reference from first citation with "Enactment" relationship
  let enacted: LawReference | null = null;
  const enactmentCitation = citations.find(
    (c) => c.relationship === 'Enactment'
  );
  if (enactmentCitation?.law) {
    enacted = {
      congress: enactmentCitation.law.congress,
      date: enactmentCitation.law.date,
      label: enactmentCitation.law.public_law_id,
      shortTitle: findShortTitle(enactmentCitation.law.public_law_id),
    };
  }

  // Build last amended reference from most recent amendment
  let lastAmended: LawReference | null = null;
  const sorted = [...amendments].sort((a, b) => b.year - a.year);
  if (sorted.length > 0) {
    const latest = sorted[0];
    lastAmended = {
      congress: latest.law.congress,
      date: latest.law.date,
      label: latest.public_law_id,
      shortTitle: findShortTitle(latest.public_law_id),
    };
  }

  return (
    <div>
      <SectionHeader
        heading={data.heading}
        breadcrumbs={breadcrumbs}
        isPositiveLaw={data.is_positive_law}
        status={data.is_repealed ? 'repealed' : null}
        enacted={enacted}
        lastAmended={lastAmended}
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
          status={data.is_repealed ? 'repealed' : null}
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
