'use client';

import { useState } from 'react';
import type { Sponsor } from '@/lib/types';

interface SponsorsSidebarProps {
    sponsors: Sponsor[];
}

const MAX_VISIBLE = 5;

function partyColor(party: string | null): string {
    if (!party) return 'text-gray-500';
    const p = party.toUpperCase();
    if (p === 'R') return 'text-red-600';
    if (p === 'D') return 'text-blue-600';
    return 'text-gray-500';
}

function SponsorRow({ sponsor }: { sponsor: Sponsor }) {
    const meta = [sponsor.party, sponsor.state].filter(Boolean).join('-');
    return (
        <div className="flex items-start gap-2 py-1.5">
            {/* Avatar placeholder */}
            <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gray-200 text-[10px] font-semibold text-gray-600">
                {sponsor.name.charAt(0)}
            </div>
            <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-xs font-medium text-gray-900 truncate">{sponsor.name}</span>
                    {sponsor.is_primary && (
                        <span className="shrink-0 rounded bg-primary-50 px-1 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary-700 ring-1 ring-inset ring-primary-200">
                            Author
                        </span>
                    )}
                </div>
                {meta && (
                    <span className={`text-[11px] font-medium ${partyColor(sponsor.party)}`}>
                        {meta}
                    </span>
                )}
            </div>
        </div>
    );
}

/** Right-panel sponsors list: primary author + cosponsors with expand toggle. */
export default function SponsorsSidebar({ sponsors }: SponsorsSidebarProps) {
    const [expanded, setExpanded] = useState(false);

    if (sponsors.length === 0) return null;

    const primary = sponsors.filter((s) => s.is_primary);
    const cosponsors = sponsors.filter((s) => !s.is_primary);

    const visibleCosponsors = expanded ? cosponsors : cosponsors.slice(0, MAX_VISIBLE);
    const hiddenCount = cosponsors.length - MAX_VISIBLE;

    return (
        <div className="rounded-md border border-gray-200 bg-white px-4 py-3">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                Sponsors
            </h3>

            {primary.map((s) => (
                <SponsorRow key={s.bioguide_id ?? s.name} sponsor={s} />
            ))}

            {cosponsors.length > 0 && (
                <>
                    {primary.length > 0 && (
                        <div className="my-1.5 border-t border-gray-100" />
                    )}
                    {visibleCosponsors.map((s) => (
                        <SponsorRow key={s.bioguide_id ?? s.name} sponsor={s} />
                    ))}
                    {!expanded && hiddenCount > 0 && (
                        <button
                            onClick={() => setExpanded(true)}
                            className="mt-1 text-xs text-primary-600 hover:text-primary-700 hover:underline"
                        >
                            +{hiddenCount} more cosponsor{hiddenCount !== 1 ? 's' : ''}
                        </button>
                    )}
                </>
            )}
        </div>
    );
}
