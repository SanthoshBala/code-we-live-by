import Link from 'next/link';
import type { SectionSummary } from '@/lib/types';
import FileIcon from './icons/FileIcon';

interface SectionNodeProps {
  section: SectionSummary;
  titleNumber: number;
  isActive?: boolean;
}

/** Leaf section node. Links directly to section viewer. */
export default function SectionNode({
  section,
  titleNumber,
  isActive,
}: SectionNodeProps) {
  return (
    <Link
      href={`/sections/${titleNumber}/${section.section_number}`}
      className={`flex items-center gap-1.5 overflow-hidden rounded px-2 py-0.5 text-xs text-gray-700 hover:bg-primary-50 hover:text-primary-700 ${isActive ? 'bg-primary-50 font-medium text-primary-700' : ''}`}
    >
      <FileIcon />
      <span className="shrink-0 whitespace-nowrap font-mono text-gray-500">
        &sect;&thinsp;{section.section_number}
      </span>
      <span className="min-w-0 truncate">{section.heading}</span>
    </Link>
  );
}
