'use client';

import { useSection } from '@/hooks/useSection';
import type { SectionNote } from '@/lib/types';
import SectionNotes from './SectionNotes';

interface NotesViewerProps {
  titleNumber: number;
  sectionNumber: string;
  file: string;
}

const FILE_TO_CATEGORY: Record<string, SectionNote['category']> = {
  EDITORIAL_NOTES: 'editorial',
  STATUTORY_NOTES: 'statutory',
  HISTORICAL_NOTES: 'historical',
};

const CATEGORY_LABELS: Record<SectionNote['category'], string> = {
  editorial: 'editorial',
  statutory: 'statutory',
  historical: 'historical',
};

/** Client component that renders notes for a single category. */
export default function NotesViewer({
  titleNumber,
  sectionNumber,
  file,
}: NotesViewerProps) {
  const { data, isLoading, error } = useSection(titleNumber, sectionNumber);
  const category = FILE_TO_CATEGORY[file];

  if (isLoading) {
    return <p className="text-gray-500">Loading notes...</p>;
  }

  if (error || !data) {
    return <p className="text-red-600">Failed to load section.</p>;
  }

  const filtered = (data.notes?.notes ?? []).filter(
    (n) => n.category === category
  );

  if (filtered.length === 0) {
    return (
      <p className="text-gray-500">
        No {CATEGORY_LABELS[category]} notes for this section.
      </p>
    );
  }

  return <SectionNotes notes={filtered} />;
}
