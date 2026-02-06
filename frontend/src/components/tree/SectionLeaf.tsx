import Link from 'next/link';
import type { SectionSummary } from '@/lib/types';
import FileIcon from './icons/FileIcon';

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
      className={`flex items-center gap-1.5 overflow-hidden rounded px-2 text-gray-700 hover:bg-primary-50 hover:text-primary-700 ${compact ? 'py-0.5 text-xs' : 'py-1 text-sm'}`}
    >
      <FileIcon />
      <span className="shrink-0 whitespace-nowrap font-mono text-gray-500">
        &sect;&thinsp;{section.section_number}
      </span>
      <span className="min-w-0 truncate">{section.heading}</span>
      <span className="ml-auto w-28 shrink-0 text-right font-mono text-xs text-gray-400">
        {section.last_amendment_law}
      </span>
      <span className="w-20 shrink-0 text-right font-mono text-xs text-gray-400">
        {section.last_amendment_year}
      </span>
    </Link>
  );
}
