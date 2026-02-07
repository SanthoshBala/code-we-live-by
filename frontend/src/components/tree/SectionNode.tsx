'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { SectionSummary } from '@/lib/types';
import TreeIndicator from './TreeIndicator';
import FileIcon from './icons/FileIcon';

interface SectionNodeProps {
  section: SectionSummary;
  titleNumber: number;
  compact?: boolean;
}

const FILE_CHILDREN = [
  'EDITORIAL_NOTES',
  'STATUTORY_NOTES',
  'HISTORICAL_NOTES',
];

/** Expandable section node showing file children (provisions + notes). */
export default function SectionNode({
  section,
  titleNumber,
  compact,
}: SectionNodeProps) {
  const [expanded, setExpanded] = useState(false);
  const basePath = `/sections/${titleNumber}/${section.section_number}`;

  return (
    <div>
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className={`flex w-full items-center gap-1.5 overflow-hidden rounded px-2 text-left text-gray-700 hover:bg-gray-100 ${compact ? 'py-0.5 text-xs' : 'py-1 text-sm'}`}
      >
        <TreeIndicator expanded={expanded} />
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
      </button>
      {expanded && (
        <div className="ml-4 border-l border-gray-300 pl-2">
          <Link
            href={basePath}
            className={`flex items-center gap-1.5 overflow-hidden rounded px-2 text-gray-700 hover:bg-primary-50 hover:text-primary-700 ${compact ? 'py-0.5 text-xs' : 'py-1 text-sm'}`}
          >
            <FileIcon />
            <span className="font-mono">{section.section_number}</span>
          </Link>
          {FILE_CHILDREN.map((file) => (
            <Link
              key={file}
              href={`${basePath}/${file}`}
              className={`flex items-center gap-1.5 overflow-hidden rounded px-2 text-gray-700 hover:bg-primary-50 hover:text-primary-700 ${compact ? 'py-0.5 text-xs' : 'py-1 text-sm'}`}
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
