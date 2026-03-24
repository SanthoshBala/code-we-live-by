'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { useLawMeta, useLawText, useLawDiffs } from '@/hooks/useLaw';
import { fetchLawText } from '@/lib/api';
import PageHeader from '@/components/ui/PageHeader';
import TabBar from '@/components/ui/TabBar';
import LawTextViewer from '@/components/law-viewer/LawTextViewer';
import LawDiffViewer from '@/components/law-viewer/LawDiffViewer';
import LawLine from '@/components/ui/LawLine';

const TABS = [
  { id: 'diff', label: 'Amendments' },
  { id: 'htm', label: 'HTM' },
  { id: 'xml', label: 'XML' },
];

export default function LawViewerPage() {
  const params = useParams<{ congress: string; lawNumber: string }>();
  const congress = Number(params.congress);
  const lawNumber = decodeURIComponent(params.lawNumber);
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState('diff');

  // Metadata is always fetched (fast — no file I/O, just a DB query)
  const {
    data: lawMeta,
    isLoading: metaLoading,
    error: metaError,
  } = useLawMeta(congress, lawNumber);

  // Prefetch HTM and XML in the background after initial render,
  // so they're already cached when the user switches tabs.
  useEffect(() => {
    if (!lawMeta) return;
    queryClient.prefetchQuery({
      queryKey: ['lawText', congress, lawNumber, 'htm'],
      queryFn: () => fetchLawText(congress, lawNumber, 'htm'),
    });
    queryClient.prefetchQuery({
      queryKey: ['lawText', congress, lawNumber, 'xml'],
      queryFn: () => fetchLawText(congress, lawNumber, 'xml'),
    });
  }, [lawMeta, congress, lawNumber, queryClient]);

  // HTM/XML content: read from cache or fetch on tab switch
  const { data: htmData, isLoading: htmLoading } = useLawText(
    congress,
    lawNumber,
    'htm',
    activeTab === 'htm'
  );
  const { data: xmlData, isLoading: xmlLoading } = useLawText(
    congress,
    lawNumber,
    'xml',
    activeTab === 'xml'
  );

  // Diffs fetched when the amendments tab is active (default)
  const { data: diffs, isLoading: diffsLoading } = useLawDiffs(
    congress,
    lawNumber,
    activeTab === 'diff'
  );

  if (metaLoading) return <p className="text-gray-500">Loading law text...</p>;
  if (metaError || !lawMeta)
    return <p className="text-red-600">Failed to load law text.</p>;

  // Title line: PL number + short title (if available)
  const title = lawMeta.short_title
    ? `PL ${congress}-${lawNumber} — ${lawMeta.short_title}`
    : `PL ${congress}-${lawNumber}`;
  // Official title always goes in subtitle
  const subtitle = lawMeta.official_title;

  const enacted = lawMeta.enacted_date
    ? {
        congress,
        lawNumber: Number(lawNumber),
        date: lawMeta.enacted_date,
        label: `PL ${congress}-${lawNumber}`,
        shortTitle: lawMeta.short_title ?? undefined,
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
          (htmLoading ? (
            <p className="text-gray-500">Loading HTM content...</p>
          ) : htmData?.htm_content ? (
            <LawTextViewer content={htmData.htm_content} />
          ) : (
            <p className="py-8 text-center text-sm text-gray-500">
              No HTM content available for this law.
            </p>
          ))}

        {activeTab === 'xml' &&
          (xmlLoading ? (
            <p className="text-gray-500">Loading XML content...</p>
          ) : xmlData?.xml_content ? (
            <LawTextViewer content={xmlData.xml_content} />
          ) : (
            <p className="py-8 text-center text-sm text-gray-500">
              No XML content available for this law.
            </p>
          ))}

        {activeTab === 'diff' && (
          <LawDiffViewer diffs={diffs ?? []} isLoading={diffsLoading} />
        )}
      </div>
    </div>
  );
}
