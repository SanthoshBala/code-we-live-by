'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useLawText, useLawAmendments } from '@/hooks/useLaw';
import PageHeader from '@/components/ui/PageHeader';
import TabBar from '@/components/ui/TabBar';
import LawTextViewer from '@/components/law-viewer/LawTextViewer';
import LawDiffViewer from '@/components/law-viewer/LawDiffViewer';
import LawLine from '@/components/ui/LawLine';

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

  // Title line: PL number + short title (if available)
  const title = lawText.short_title
    ? `PL ${congress}-${lawNumber} — ${lawText.short_title}`
    : `PL ${congress}-${lawNumber}`;
  // Official title always goes in subtitle
  const subtitle = lawText.official_title;

  const enacted = lawText.enacted_date
    ? {
        congress,
        lawNumber: Number(lawNumber),
        date: lawText.enacted_date,
        label: `PL ${congress}-${lawNumber}`,
        shortTitle: lawText.short_title ?? undefined,
      }
    : null;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title={title}
        subtitle={subtitle}
        badges={
          enacted ? (
            <dl className="grid grid-cols-[auto_auto_auto_auto_auto] gap-x-3 gap-y-0.5">
              <LawLine label="Enacted:" law={enacted} />
            </dl>
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
