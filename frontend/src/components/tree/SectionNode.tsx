'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { SectionSummary } from '@/lib/types';
import TreeIndicator from './TreeIndicator';
import FileIcon from './icons/FileIcon';

interface SectionNodeProps {
  section: SectionSummary;
  titleNumber: number;
  isActive?: boolean;
}

const NOTE_FILES: { file: string; category: string }[] = [
  { file: 'EDITORIAL_NOTES', category: 'editorial' },
  { file: 'STATUTORY_NOTES', category: 'statutory' },
  { file: 'HISTORICAL_NOTES', category: 'historical' },
];

/** Expandable section node showing file children (Code + notes). */
export default function SectionNode({
  section,
  titleNumber,
  isActive,
}: SectionNodeProps) {
  const [expanded, setExpanded] = useState(!!isActive);
  const basePath = `/sections/${titleNumber}/${section.section_number}`;
  const noteCategories = section.note_categories ?? [];
  const noteFiles = NOTE_FILES.filter(({ category }) =>
    noteCategories.includes(category)
  );

  return (
    <div>
      <div
        className={`flex w-full items-center gap-1 rounded px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-100 ${isActive ? 'bg-primary-50' : ''}`}
      >
        <TreeIndicator
          expanded={expanded}
          onToggle={() => setExpanded((prev) => !prev)}
        />
        <Link
          href={basePath}
          className="flex min-w-0 items-center gap-1.5 overflow-hidden hover:text-primary-700"
        >
          <span className="shrink-0 whitespace-nowrap font-mono text-gray-500">
            &sect;&thinsp;{section.section_number}
          </span>
          <span className="min-w-0 truncate">{section.heading}</span>
        </Link>
      </div>
      {expanded && (
        <div className="ml-4 border-l border-gray-300 pl-2">
          <Link
            href={`${basePath}/CODE`}
            className="flex items-center gap-1.5 rounded px-2 py-0.5 text-xs text-gray-700 hover:bg-primary-50 hover:text-primary-700"
          >
            <FileIcon />
            <span className="font-mono">CODE</span>
          </Link>
          {noteFiles.map(({ file }) => (
            <Link
              key={file}
              href={`${basePath}/${file}`}
              className="flex items-center gap-1.5 rounded px-2 py-0.5 text-xs text-gray-700 hover:bg-primary-50 hover:text-primary-700"
            >
              <FileIcon />
              <span className="font-mono">{file}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
