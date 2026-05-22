'use client';

import { useState } from 'react';
import type { TimelineEvent as TimelineEventType } from '@/lib/types';
import TimelineEvent from './TimelineEvent';

interface LegislativeHistoryTimelineProps {
  events: TimelineEventType[];
}

/** Remove duplicate and redundant events from the raw timeline. */
function deduplicateEvents(events: TimelineEventType[]): TimelineEventType[] {
  const seen = new Set<string>();

  // Collect dates where a proper vote event already exists.
  const voteDateKeys = new Set<string>();
  for (const e of events) {
    if (
      (e.event_type === 'house_vote' || e.event_type === 'senate_vote') &&
      e.date
    ) {
      voteDateKeys.add(`${e.event_type}|${e.date}`);
    }
  }

  const result: TimelineEventType[] = [];
  for (const e of events) {
    const key = `${e.event_type}|${e.date}|${e.title}`;
    if (seen.has(key)) continue;
    seen.add(key);

    // Drop "other"-typed passage actions that duplicate a proper vote event on
    // the same date (e.g. "Passed/agreed to in Senate" alongside a senate_vote).
    if (e.event_type === 'other' && e.date) {
      const lower = (e.title + ' ' + e.description).toLowerCase();
      const isPassage = ['passed', 'agreed to', 'adopted'].some((kw) =>
        lower.includes(kw)
      );
      if (
        isPassage &&
        (voteDateKeys.has(`senate_vote|${e.date}`) ||
          voteDateKeys.has(`house_vote|${e.date}`))
      ) {
        continue;
      }
    }

    result.push(e);
  }
  return result;
}

type RenderItem =
  | { kind: 'event'; event: TimelineEventType; idx: number }
  | { kind: 'year'; year: number };

/** Interleave year separator items before the first event of each new year. */
function buildRenderItems(events: TimelineEventType[]): RenderItem[] {
  const items: RenderItem[] = [];
  let currentYear: number | null = null;

  events.forEach((event, idx) => {
    if (event.date) {
      const year = parseInt(event.date.split('-')[0], 10);
      if (!isNaN(year) && year !== currentYear) {
        items.push({ kind: 'year', year });
        currentYear = year;
      }
    }
    items.push({ kind: 'event', event, idx });
  });

  return items;
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

/** Year separator shown between groups of events from different years. */
function YearSeparator({
  year,
  view,
}: {
  year: number;
  view: 'condensed' | 'expanded';
}) {
  const heightCls = view === 'condensed' ? 'h-7 w-7' : 'h-9 w-9';
  return (
    <li className="relative flex items-center gap-3 py-1">
      {/* Transparent spacer aligns with the icon column */}
      <span className={`shrink-0 ${heightCls}`} aria-hidden />
      <div className="flex flex-1 items-center gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-gray-400">
          {year}
        </span>
        <span className="h-px flex-1 bg-gray-100" aria-hidden />
      </div>
    </li>
  );
}

/** Discussion panel with Condensed/Expanded toggle. */
export default function LegislativeHistoryTimeline({
  events,
}: LegislativeHistoryTimelineProps) {
  const [view, setView] = useState<'condensed' | 'expanded'>('expanded');

  const dedupedEvents = deduplicateEvents(events);

  if (dedupedEvents.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white px-4 py-8 text-center text-sm text-gray-500">
        No legislative history available for this law.
      </div>
    );
  }

  const items = buildRenderItems(dedupedEvents);

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {/* Panel header */}
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-900">Discussion</h3>
          <span className="mono text-xs text-gray-400">
            {dedupedEvents.length} entries
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
          {items.map((item, i) =>
            item.kind === 'year' ? (
              <YearSeparator
                key={`year-${item.year}-${i}`}
                year={item.year}
                view="condensed"
              />
            ) : (
              <TimelineEvent
                key={item.idx}
                event={item.event}
                view="condensed"
              />
            )
          )}
        </ol>
      ) : (
        /* Expanded pill-cards */
        <ol className="relative space-y-3 px-4 py-3">
          <span
            className="absolute bottom-4 left-[33px] top-4 w-px bg-gray-200"
            aria-hidden
          />
          {items.map((item, i) =>
            item.kind === 'year' ? (
              <YearSeparator
                key={`year-${item.year}-${i}`}
                year={item.year}
                view="expanded"
              />
            ) : (
              <TimelineEvent
                key={item.idx}
                event={item.event}
                view="expanded"
              />
            )
          )}
        </ol>
      )}
    </div>
  );
}
