'use client';

import { useState } from 'react';
import type { StandaloneProvision } from '@/lib/types';

interface StandaloneProvisionsPanelProps {
  provisions: StandaloneProvision[];
}

function ProvisionCard({ provision }: { provision: StandaloneProvision }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = provision.full_text.length > provision.text_excerpt.length;
  const displayText = expanded ? provision.full_text : provision.text_excerpt;

  return (
    <div className="rounded-md border border-gray-200 bg-white p-4">
      <div className="mb-2 flex flex-wrap items-start gap-2">
        <span className="font-mono text-sm font-semibold text-gray-800">
          {provision.section_num}
        </span>
        {provision.heading && (
          <span className="text-sm font-medium text-gray-700">
            {provision.heading}
          </span>
        )}
        <span className="ml-auto shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
          Not codified in US Code
        </span>
      </div>

      <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-600">
        {displayText}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        {isLong && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-xs font-medium text-primary-600 hover:underline"
          >
            {expanded ? 'Show less' : 'Show full text'}
          </button>
        )}
        {provision.govinfo_url && (
          <a
            href={provision.govinfo_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-medium text-primary-600 hover:underline"
          >
            View on GovInfo →
          </a>
        )}
      </div>
    </div>
  );
}

/** Collapsible panel listing freestanding law provisions not codified in the US Code. */
export default function StandaloneProvisionsPanel({
  provisions,
}: StandaloneProvisionsPanelProps) {
  const [open, setOpen] = useState(false);
  const count = provisions.length;

  return (
    <div className="mt-6 rounded-lg border border-gray-200">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2">
          <span
            className="text-sm text-gray-500 transition-transform duration-150"
            style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)' }}
          >
            ▶
          </span>
          <span className="text-sm font-semibold text-gray-900">
            Standalone Provisions
          </span>
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
            {count} {count === 1 ? 'provision' : 'provisions'}
          </span>
        </div>
        <span className="text-xs text-gray-400">
          Sections not codified in the US Code
        </span>
      </button>

      {open && (
        <div className="border-t border-gray-200 px-4 py-4">
          <div className="space-y-3">
            {provisions.map((p, i) => (
              <ProvisionCard key={i} provision={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
