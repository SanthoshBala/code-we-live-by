'use client';

import { useState } from 'react';
import type { TimelineEvent as TimelineEventType } from '@/lib/types';
import TimelineEvent from './TimelineEvent';

interface LegislativeHistoryTimelineProps {
    events: TimelineEventType[];
}

/** Scrollable timeline of legislative events with milestone/full toggle. */
export default function LegislativeHistoryTimeline({ events }: LegislativeHistoryTimelineProps) {
    const [showAll, setShowAll] = useState(false);

    const milestones = events.filter((e) => e.is_milestone);
    const displayed = showAll ? events : milestones;
    const hasNonMilestones = events.length > milestones.length;

    if (events.length === 0) {
        return (
            <p className="py-8 text-center text-sm text-gray-500">
                No legislative history available for this law.
            </p>
        );
    }

    return (
        <div className="flex flex-col">
            {/* Header */}
            <div className="mb-2 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-900">
                    Discussion
                    <span className="ml-2 font-normal text-gray-400">
                        {displayed.length} event{displayed.length !== 1 ? 's' : ''}
                        {!showAll && hasNonMilestones && ` of ${events.length}`}
                    </span>
                </h2>
                {hasNonMilestones && (
                    <button
                        onClick={() => setShowAll((v) => !v)}
                        className="text-xs text-primary-600 hover:text-primary-700 hover:underline"
                    >
                        {showAll ? 'Show milestones only' : `Show all ${events.length} events`}
                    </button>
                )}
            </div>

            {/* Event list with vertical connector line */}
            <div className="relative">
                {/* Connector line */}
                <div className="absolute left-[7px] top-4 bottom-4 w-px bg-gray-200" aria-hidden />

                <div className="divide-y divide-gray-100">
                    {displayed.map((event, i) => (
                        <TimelineEvent key={i} event={event} />
                    ))}
                </div>
            </div>
        </div>
    );
}
