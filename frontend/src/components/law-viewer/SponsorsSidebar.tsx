'use client';

import { useState } from 'react';
import type { Sponsor } from '@/lib/types';

interface SponsorsSidebarProps {
  sponsors: Sponsor[];
}

const MAX_VISIBLE = 5;

/**
 * Normalize a sponsor name for display.
 *
 * Congress.gov sometimes returns names in "Last, First" format or with a
 * trailing party/district annotation like "[R-CA-42]". This converts both
 * to a plain "First Last" string.
 */
export function formatSponsorName(raw: string): string {
  // Strip trailing "[R-CA-42]", "(D-CA)", "[R-KY-5]", etc.
  let name = raw
    .replace(/\s*[\[(][A-Z]-[A-Z]{1,3}(?:-\d+)?[\])]\s*$/, '')
    .trim();

  // Convert "Last, First [Middle]" → "First [Middle] Last"
  const comma = name.indexOf(',');
  if (comma > 0 && comma < name.length - 1) {
    const last = name.slice(0, comma).trim();
    const first = name.slice(comma + 1).trim();
    return `${first} ${last}`;
  }
  return name;
}

function getInitials(displayName: string): string {
  const initials = displayName
    .split(' ')
    .filter((w) => /^[A-Z]/.test(w))
    .map((w) => w[0])
    .join('')
    .slice(0, 2);
  return initials || '?';
}

function partyColor(party: string | null): string {
  if (!party) return 'text-gray-500';
  const p = party.toUpperCase();
  if (p === 'R') return 'text-red-600';
  if (p === 'D') return 'text-blue-600';
  return 'text-gray-500';
}

/** Format "R-CA" or "R-CA (42)" for representatives, "D-CA" for senators. */
function formatMeta(sponsor: Sponsor): string {
  const parts = [sponsor.party, sponsor.state].filter(Boolean).join('-');
  if (!parts) return '';
  if (sponsor.district != null) {
    return `${parts} (${sponsor.district})`;
  }
  return parts;
}

function SponsorRow({ sponsor }: { sponsor: Sponsor }) {
  const displayName = formatSponsorName(sponsor.name);
  const initials = getInitials(displayName);
  const meta = formatMeta(sponsor);

  return (
    <div className="flex items-start gap-2 py-1.5">
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gray-200 text-[10px] font-semibold text-gray-600">
        {initials}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="truncate text-xs font-medium text-gray-900">
            {displayName}
          </span>
          {sponsor.is_primary && (
            <span className="ring-primary-200 shrink-0 rounded bg-primary-50 px-1 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary-700 ring-1 ring-inset">
              Author
            </span>
          )}
        </div>
        {meta && (
          <span
            className={`text-[11px] font-medium ${partyColor(sponsor.party)}`}
          >
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
  const cosponsors = [...sponsors.filter((s) => !s.is_primary)].sort((a, b) =>
    formatSponsorName(a.name).localeCompare(formatSponsorName(b.name))
  );

  const visibleCosponsors = expanded
    ? cosponsors
    : cosponsors.slice(0, MAX_VISIBLE);
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
