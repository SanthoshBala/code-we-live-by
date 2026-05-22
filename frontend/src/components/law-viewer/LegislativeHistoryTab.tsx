'use client';

import type { ChamberVote, LegislativeHistory, LawText } from '@/lib/types';
import CBOEstimatesPanel from './CBOEstimatesPanel';
import LegislativeHistoryTimeline from './LegislativeHistoryTimeline';
import RelatedBillsPanel from './RelatedBillsPanel';
import SponsorsSidebar, { formatSponsorName } from './SponsorsSidebar';

interface LegislativeHistoryTabProps {
  history: LegislativeHistory;
  lawMeta?: LawText | null;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  const [year, month, day] = dateStr.split('-');
  return `${year}.${month}.${day}`;
}

function daysBetween(a: string | null, b: string | null): number | null {
  if (!a || !b) return null;
  const diff = new Date(b).getTime() - new Date(a).getTime();
  return Math.round(diff / (1000 * 60 * 60 * 24));
}

/** Compact chamber vote row shown in the header banner. */
function MiniVote({ vote }: { vote: ChamberVote }) {
  const passed = vote.yeas > vote.nays;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="mono w-14 shrink-0 text-[10px] uppercase tracking-wider text-gray-500">
        {vote.chamber}
      </span>
      <span
        className={`mono text-[11px] font-semibold ${passed ? 'text-emerald-700' : 'text-red-700'}`}
      >
        {vote.yeas}–{vote.nays}
      </span>
      <span className="truncate text-[11px] text-gray-500">
        {passed ? 'Passed' : 'Failed'}
      </span>
    </div>
  );
}

/** Top banner: law title, sponsor intro, and compact vote summaries. */
function HeaderBanner({
  history,
  lawMeta,
}: {
  history: LegislativeHistory;
  lawMeta?: LawText | null;
}) {
  const shortTitle = lawMeta?.short_title ?? null;
  const primarySponsor = history.sponsors.find((s) => s.is_primary);
  const introducedDate = history.timeline.find(
    (e) => e.event_type === 'introduced'
  )?.date;
  const days = daysBetween(introducedDate ?? null, history.enacted_date);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {shortTitle && (
            <h2 className="text-base font-semibold text-gray-900">
              {shortTitle}
            </h2>
          )}
          <p className="mt-0.5 text-sm text-gray-500">
            {primarySponsor && (
              <>
                <span className="mono font-medium text-gray-700">
                  {formatSponsorName(primarySponsor.name)}
                </span>{' '}
                introduced this legislation
                {days !== null && (
                  <>
                    {' · '}
                    <span className="mono">{days}</span> days in Congress
                  </>
                )}
              </>
            )}
            {history.enacted_date && (
              <>
                {primarySponsor ? ' · enacted ' : 'Enacted '}
                <span className="mono font-medium text-gray-700">
                  {formatDate(history.enacted_date)}
                </span>
              </>
            )}
          </p>
        </div>

        {history.chamber_votes.length > 0 && (
          <div className="w-56 shrink-0 space-y-1 border-l border-gray-100 pl-4">
            {history.chamber_votes.map((v) => (
              <MiniVote key={v.chamber} vote={v} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** Small president card shown in the right sidebar. */
function PresidentCard({ history }: { history: LegislativeHistory }) {
  const { presidential_action, president_name, enacted_date, status } = history;
  if (!president_name && !presidential_action) return null;

  const isVetoed = status === 'vetoed';
  const isEnacted = status === 'enacted';

  const initials = president_name
    ? president_name
        .split(' ')
        .filter((w) => /^[A-Z]/.test(w))
        .map((w) => w[0])
        .join('')
        .slice(0, 2)
    : '?';

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2.5">
        <h3 className="text-sm font-semibold text-gray-900">President</h3>
        <span className="mono text-[10px] uppercase tracking-wider text-gray-400">
          {isVetoed ? 'vetoed' : isEnacted ? 'signed into law' : 'pending'}
        </span>
      </div>
      <div className="flex items-center gap-3 px-4 py-2.5">
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
            isVetoed
              ? 'bg-red-100 text-red-700'
              : 'bg-primary-100 text-primary-700'
          }`}
        >
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-gray-900">
            {president_name ?? presidential_action}
          </p>
          {enacted_date && (
            <p className="mono mt-0.5 text-[11px] text-gray-400">
              {formatDate(enacted_date)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/** Banner shown when a bill was vetoed or is still pending. */
function StatusBanner({ status }: { status: LegislativeHistory['status'] }) {
  if (status === 'enacted') return null;

  if (status === 'vetoed') {
    return (
      <div className="mb-4 flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-2.5">
        <svg
          className="h-4 w-4 shrink-0 text-red-600"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <circle cx="8" cy="8" r="6" />
          <line x1="5" y1="8" x2="11" y2="8" />
        </svg>
        <p className="text-sm font-semibold text-red-700">
          This bill was vetoed and did not become law.
        </p>
      </div>
    );
  }

  return (
    <div className="mb-4 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-2.5">
      <svg
        className="h-4 w-4 shrink-0 text-amber-600"
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <circle cx="8" cy="8" r="6" />
        <line x1="8" y1="5" x2="8" y2="9" />
        <circle cx="8" cy="11" r="0.75" fill="currentColor" stroke="none" />
      </svg>
      <p className="text-sm font-medium text-amber-700">
        This bill is pending — it has not yet been enacted or vetoed.
      </p>
    </div>
  );
}

/** PR-style legislative history tab: header banner + 8/4 two-column grid. */
export default function LegislativeHistoryTab({
  history,
  lawMeta,
}: LegislativeHistoryTabProps) {
  return (
    <div className="space-y-4">
      <StatusBanner status={history.status} />

      <HeaderBanner history={history} lawMeta={lawMeta} />

      <div className="grid grid-cols-12 gap-4">
        {/* Left column — Discussion timeline (8/12) */}
        <div className="col-span-12 lg:col-span-8">
          <LegislativeHistoryTimeline events={history.timeline} />
        </div>

        {/* Right column — sidebar (4/12) */}
        <div className="col-span-12 space-y-4 lg:col-span-4">
          <SponsorsSidebar sponsors={history.sponsors} />
          <PresidentCard history={history} />
          <CBOEstimatesPanel estimates={history.cbo_estimates ?? []} />
          <RelatedBillsPanel bills={history.related_bills ?? []} />
        </div>
      </div>
    </div>
  );
}
