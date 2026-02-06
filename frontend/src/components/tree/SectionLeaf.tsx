import Link from 'next/link';
import type { SectionSummary } from '@/lib/types';

interface SectionLeafProps {
  section: SectionSummary;
  titleNumber: number;
  compact?: boolean;
}

/** Leaf node linking to a section viewer page. */
export default function SectionLeaf({
  section,
  titleNumber,
  compact,
}: SectionLeafProps) {
  return (
    <Link
      href={`/sections/${titleNumber}/${section.section_number}`}
      className={`block rounded px-2 text-gray-700 hover:bg-primary-50 hover:text-primary-700 ${compact ? 'py-0.5 text-xs' : 'py-1 text-sm'}`}
    >
      <span className="font-mono text-gray-500">
        &sect;&thinsp;{section.section_number}
      </span>{' '}
      {section.heading}
    </Link>
  );
}
