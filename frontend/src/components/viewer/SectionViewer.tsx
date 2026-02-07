'use client';

import { useSection } from '@/hooks/useSection';
import SectionHeader from './SectionHeader';
import SectionProvisions from './SectionProvisions';

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

  if (isLoading) {
    return <p className="text-gray-500">Loading section...</p>;
  }

  if (error || !data) {
    return <p className="text-red-600">Failed to load section.</p>;
  }

  return (
    <div>
      <SectionHeader
        fullCitation={data.full_citation}
        heading={data.heading}
        enactedDate={data.enacted_date}
        lastModifiedDate={data.last_modified_date}
        isPositiveLaw={data.is_positive_law}
        isRepealed={data.is_repealed}
      />
      <SectionProvisions
        fullCitation={data.full_citation}
        heading={data.heading}
        textContent={data.text_content}
        isRepealed={data.is_repealed}
      />
    </div>
  );
}
