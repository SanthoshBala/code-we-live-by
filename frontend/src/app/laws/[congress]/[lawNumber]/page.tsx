'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useLawText, useLawAmendments } from '@/hooks/useLaw';
import PageHeader from '@/components/ui/PageHeader';
import TabBar from '@/components/ui/TabBar';
import LawTextViewer from '@/components/law-viewer/LawTextViewer';
import LawDiffViewer from '@/components/law-viewer/LawDiffViewer';

const TABS = [
  { id: 'htm', label: 'HTM Text' },
  { id: 'xml', label: 'XML Text' },
  { id: 'diff', label: 'Diff View' },
];

export default function LawViewerPage() {
  const params = useParams<{ congress: string; lawNumber: string }>();
  const congress = Number(params.congress);
  const lawNumber = decodeURIComponent(params.lawNumber);

  const [activeTab, setActiveTab] = useState('htm');

  const {
    data: lawText,
    isLoading: textLoading,
    error: textError,
  } = useLawText(congress, lawNumber);

  const { data: amendments, isLoading: amendmentsLoading } = useLawAmendments(
    congress,
    lawNumber,
    activeTab === 'diff'
  );

  if (textLoading) return <p className="text-gray-500">Loading law text...</p>;
  if (textError || !lawText)
    return <p className="text-red-600">Failed to load law text.</p>;

  const shortTitle = lawText.short_title || lawText.official_title;
  const title = shortTitle
    ? `PL ${congress}-${lawNumber} — ${shortTitle}`
    : `PL ${congress}-${lawNumber}`;

  const dateBadges: { label: string; date: string }[] = [];
  if (lawText.introduced_date)
    dateBadges.push({ label: 'Introduced', date: lawText.introduced_date });
  if (lawText.house_passed_date)
    dateBadges.push({ label: 'House', date: lawText.house_passed_date });
  if (lawText.senate_passed_date)
    dateBadges.push({ label: 'Senate', date: lawText.senate_passed_date });
  if (lawText.presented_to_president_date)
    dateBadges.push({
      label: 'Presented',
      date: lawText.presented_to_president_date,
    });
  if (lawText.enacted_date)
    dateBadges.push({ label: 'Enacted', date: lawText.enacted_date });
  if (lawText.effective_date)
    dateBadges.push({ label: 'Effective', date: lawText.effective_date });

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title={title}
        badges={
          dateBadges.length > 0 ? (
            <>
              {dateBadges.map(({ label, date }) => (
                <span
                  key={label}
                  className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600"
                >
                  {label} {date}
                </span>
              ))}
            </>
          ) : undefined
        }
      />

      <div className="mt-4">
        <TabBar tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      </div>

      <div className="mt-4">
        {activeTab === 'htm' &&
          (lawText.htm_content ? (
            <LawTextViewer content={lawText.htm_content} />
          ) : (
            <p className="py-8 text-center text-sm text-gray-500">
              No HTM content available for this law.
            </p>
          ))}

        {activeTab === 'xml' &&
          (lawText.xml_content ? (
            <LawTextViewer content={lawText.xml_content} />
          ) : (
            <p className="py-8 text-center text-sm text-gray-500">
              No XML content available for this law.
            </p>
          ))}

        {activeTab === 'diff' && (
          <LawDiffViewer
            amendments={amendments ?? []}
            isLoading={amendmentsLoading}
          />
        )}
      </div>
    </div>
  );
}
