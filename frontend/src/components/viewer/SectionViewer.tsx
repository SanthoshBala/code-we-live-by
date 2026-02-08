'use client';

import { useState } from 'react';
import { useSection } from '@/hooks/useSection';
import SectionHeader from './SectionHeader';
import SectionProvisions from './SectionProvisions';
import AmendmentList from './AmendmentList';
import CitationList from './CitationList';

interface SectionViewerProps {
  titleNumber: number;
  sectionNumber: string;
}

/** Client component that fetches and renders section provisions. */
export default function SectionViewer({
  titleNumber,
  sectionNumber,
}: SectionViewerProps) {
  const { data, isLoading, error } = useSection(titleNumber, sectionNumber);
  const [activeTab, setActiveTab] = useState<'code' | 'history'>('code');

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
        fullCitation={data.full_citation}
        heading={data.heading}
        enactedDate={data.enacted_date}
        lastModifiedDate={data.last_modified_date}
        isPositiveLaw={data.is_positive_law}
        isRepealed={data.is_repealed}
        latestAmendment={latestAmendment}
      />
      {hasHistory && (
        <div
          role="tablist"
          className="mb-4 flex border-b border-gray-200 text-sm font-medium"
        >
          <button
            role="tab"
            aria-selected={activeTab === 'code'}
            onClick={() => setActiveTab('code')}
            className={`px-4 py-2 ${activeTab === 'code' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Code
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'history'}
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 ${activeTab === 'history' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
          >
            History
          </button>
        </div>
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
