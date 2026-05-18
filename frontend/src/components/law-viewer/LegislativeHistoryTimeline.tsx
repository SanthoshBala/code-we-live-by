'use client';

import { useState } from 'react';
import type { TimelineEvent as TimelineEventType } from '@/lib/types';
import TimelineEvent from './TimelineEvent';

interface LegislativeHistoryTimelineProps {
  events: TimelineEventType[];
}

/** Segmented toggle button pair. */
function ViewToggle({
  view,
  onChange,
}: {
  view: 'condensed' | 'expanded';
  onChange: (v: 'condensed' | 'expanded') => void;
}) {
  return (
    <div className="inline-flex rounded-md border border-gray-200 bg-gray-50 p-0.5 text-[11px]">
      {(
        [
          ['condensed', 'Condensed'],
          ['expanded', 'Expanded'],
        ] as const
      ).map(([k, label]) => (
        <button
          key={k}
          onClick={() => onChange(k)}
          className={`mono rounded px-2 py-0.5 font-semibold transition ${
            view === k
              ? 'bg-white text-gray-900 shadow-sm ring-1 ring-gray-200'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/** Discussion panel with Condensed/Expanded toggle. */
export default function LegislativeHistoryTimeline({
  events,
}: LegislativeHistoryTimelineProps) {
  const [view, setView] = useState<'condensed' | 'expanded'>('expanded');

  if (events.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white px-4 py-8 text-center text-sm text-gray-500">
        No legislative history available for this law.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {/* Panel header */}
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-900">Discussion</h3>
          <span className="mono text-xs text-gray-400">
            {events.length} entries
          </span>
        </div>
        <ViewToggle view={view} onChange={setView} />
      </div>

      {view === 'condensed' ? (
        /* One-line rows */
        <ol className="relative px-4 py-2">
          <span
            className="absolute bottom-3 left-[33px] top-3 w-px bg-gray-200"
            aria-hidden
          />
          {events.map((event, i) => (
            <TimelineEvent key={i} event={event} view="condensed" />
          ))}
        </ol>
      ) : (
        /* Expanded pill-cards */
        <ol className="relative space-y-3 px-4 py-3">
          <span
            className="absolute bottom-4 left-[33px] top-4 w-px bg-gray-200"
            aria-hidden
          />
          {events.map((event, i) => (
            <TimelineEvent key={i} event={event} view="expanded" />
          ))}
        </ol>
      )}
    </div>
  );
}
