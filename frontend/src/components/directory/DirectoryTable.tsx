'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { DirectoryItem, ItemStatus } from '@/lib/types';
import FolderIcon from '@/components/tree/icons/FolderIcon';
import FileIcon from '@/components/tree/icons/FileIcon';

type SortKey = 'id' | 'name' | 'sectionCount' | 'lastAmendment' | 'date';
type SortDir = 'asc' | 'desc';

interface DirectoryTableProps {
  items: DirectoryItem[];
}

function compareItems(
  a: DirectoryItem,
  b: DirectoryItem,
  key: SortKey
): number {
  switch (key) {
    case 'id':
      return a.id.localeCompare(b.id, undefined, { numeric: true });
    case 'name':
      return a.name.localeCompare(b.name);
    case 'sectionCount':
      return (a.sectionCount ?? 0) - (b.sectionCount ?? 0);
    case 'lastAmendment':
      return (a.lastAmendmentLaw ?? '').localeCompare(b.lastAmendmentLaw ?? '');
    case 'date':
      return (a.lastAmendmentYear ?? 0) - (b.lastAmendmentYear ?? 0);
  }
}

function SortIndicator({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return null;
  return (
    <span
      className="ml-1"
      aria-label={dir === 'asc' ? 'sorted ascending' : 'sorted descending'}
    >
      {dir === 'asc' ? '\u2191' : '\u2193'}
    </span>
  );
}

/** Table showing child items with sortable ID, Name, # Sections, Last Amendment, and Date columns. */
export default function DirectoryTable({ items }: DirectoryTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('id');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const hasSectionCounts = items.some((item) => item.sectionCount != null);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  const sorted = [...items].sort((a, b) => {
    // Always show folders before files
    if (a.kind !== b.kind) return a.kind === 'folder' ? -1 : 1;
    const cmp = compareItems(a, b, sortKey);
    return sortDir === 'asc' ? cmp : -cmp;
  });

  if (items.length === 0) {
    return <p className="text-sm text-gray-400">No items found.</p>;
  }

  const thClass =
    'cursor-pointer select-none whitespace-nowrap pb-2 pr-2 hover:text-gray-700';

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-left text-xs font-semibold text-gray-500">
          <th className={thClass} onClick={() => handleSort('id')}>
            ID
            <SortIndicator active={sortKey === 'id'} dir={sortDir} />
          </th>
          <th
            className={`${thClass} w-full`}
            onClick={() => handleSort('name')}
          >
            Name
            <SortIndicator active={sortKey === 'name'} dir={sortDir} />
          </th>
          {hasSectionCounts && (
            <th
              className={`${thClass} text-right`}
              onClick={() => handleSort('sectionCount')}
            >
              # Sections
              <SortIndicator
                active={sortKey === 'sectionCount'}
                dir={sortDir}
              />
            </th>
          )}
          <th
            className={`${thClass} text-right`}
            onClick={() => handleSort('lastAmendment')}
          >
            Last amended by
            <SortIndicator active={sortKey === 'lastAmendment'} dir={sortDir} />
          </th>
          <th
            className={`${thClass} text-right`}
            onClick={() => handleSort('date')}
          >
            Date
            <SortIndicator active={sortKey === 'date'} dir={sortDir} />
          </th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((item) => {
          const status: ItemStatus = item.status ?? null;
          return (
            <tr
              key={item.href}
              className="border-b border-gray-100 hover:bg-gray-50"
            >
              <td className="whitespace-nowrap py-2 pr-2">
                <Link
                  href={item.href}
                  className="flex items-center gap-2 text-gray-800 hover:text-primary-700"
                >
                  {item.kind === 'folder' ? (
                    <FolderIcon open={false} status={status} />
                  ) : (
                    <FileIcon status={status} />
                  )}
                  <span className="font-mono text-xs">{item.id}</span>
                </Link>
              </td>
              <td className="max-w-0 truncate py-2 pr-2">
                <Link
                  href={item.href}
                  className="text-gray-800 hover:text-primary-700"
                >
                  {item.name}
                </Link>
              </td>
              {hasSectionCounts && (
                <td className="whitespace-nowrap py-2 pr-2 text-right text-xs text-gray-500">
                  {item.sectionCount ?? ''}
                </td>
              )}
              <td className="whitespace-nowrap py-2 pr-2 text-right font-mono text-xs text-gray-500">
                {item.lastAmendmentLaw ?? ''}
              </td>
              <td className="whitespace-nowrap py-2 text-right font-mono text-xs text-gray-500">
                {item.lastAmendmentYear ?? ''}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
