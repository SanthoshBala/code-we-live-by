import type { LegislativeHistory } from '@/lib/types';
import LegislativeHistoryTimeline from './LegislativeHistoryTimeline';
import SponsorsSidebar from './SponsorsSidebar';
import VotesSidebar from './VotesSidebar';

interface LegislativeHistoryTabProps {
    history: LegislativeHistory;
}

function formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    const [year, month, day] = dateStr.split('-');
    return `${year}.${month}.${day}`;
}

function PresidentialActionCard({
    history,
}: {
    history: LegislativeHistory;
}) {
    const { presidential_action, president_name, enacted_date, status } = history;
    if (!presidential_action && !president_name) return null;

    const isEnacted = status === 'enacted';
    const isVetoed = status === 'vetoed';

    return (
        <div
            className={`rounded-md border px-4 py-3 ${
                isVetoed
                    ? 'border-red-200 bg-red-50'
                    : isEnacted
                      ? 'border-green-200 bg-green-50'
                      : 'border-gray-200 bg-white'
            }`}
        >
            <div className="flex items-start gap-2">
                {/* White House icon */}
                <svg
                    className={`mt-0.5 h-4 w-4 shrink-0 ${isVetoed ? 'text-red-600' : isEnacted ? 'text-green-600' : 'text-gray-400'}`}
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                >
                    <path d="M3 12 L3 7 L8 3 L13 7 L13 12 Z" />
                    <rect x="6" y="9" width="4" height="3" />
                </svg>
                <div className="min-w-0 flex-1">
                    <p className={`text-xs font-semibold ${isVetoed ? 'text-red-700' : isEnacted ? 'text-green-700' : 'text-gray-700'}`}>
                        {presidential_action ?? (isEnacted ? 'Signed into law' : 'Presidential action')}
                    </p>
                    {president_name && (
                        <p className="mt-0.5 text-[11px] text-gray-500">
                            {president_name}
                        </p>
                    )}
                    {enacted_date && (
                        <p className="mt-0.5 font-mono text-[11px] text-gray-400">
                            {formatDate(enacted_date)}
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}

function StatusBanner({ status }: { status: LegislativeHistory['status'] }) {
    if (status === 'enacted') return null;

    if (status === 'vetoed') {
        return (
            <div className="mb-4 flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-2.5">
                <svg className="h-4 w-4 shrink-0 text-red-600" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
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
            <svg className="h-4 w-4 shrink-0 text-amber-600" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
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

/** 2-column (2:1) layout: timeline left, presidential card + votes + sponsors right. */
export default function LegislativeHistoryTab({ history }: LegislativeHistoryTabProps) {
    return (
        <div>
            <StatusBanner status={history.status} />
            <div className="grid grid-cols-3 gap-6">
                {/* Left column — timeline (2/3 width) */}
                <div className="col-span-2 overflow-y-auto">
                    <LegislativeHistoryTimeline events={history.timeline} />
                </div>

                {/* Right column — sidebar cards (1/3 width) */}
                <div className="col-span-1 flex flex-col gap-4">
                    <PresidentialActionCard history={history} />
                    <VotesSidebar votes={history.chamber_votes} />
                    <SponsorsSidebar sponsors={history.sponsors} />
                </div>
            </div>
        </div>
    );
}
