import type {
  AmendmentStatus,
  TimelineEvent as TimelineEventType,
} from '@/lib/types';

interface TimelineEventProps {
  event: TimelineEventType;
  view: 'condensed' | 'expanded';
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  const [year, month, day] = dateStr.split('-');
  return `${year}.${month}.${day}`;
}

// ── Icons ──────────────────────────────────────────────────────────────────

function EventIcon({
  eventType,
}: {
  eventType: TimelineEventType['event_type'];
}) {
  const cls = 'h-4 w-4 shrink-0';
  switch (eventType) {
    case 'introduced':
      return (
        <svg
          className={cls}
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <circle cx="8" cy="8" r="6" />
          <line x1="8" y1="5" x2="8" y2="8" />
          <circle cx="8" cy="10.5" r="0.75" fill="currentColor" stroke="none" />
        </svg>
      );
    case 'committee_referral':
      return (
        <svg
          className={cls}
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <rect x="2" y="3" width="12" height="10" rx="1" />
          <line x1="5" y1="7" x2="11" y2="7" />
          <line x1="5" y1="10" x2="9" y2="10" />
        </svg>
      );
    case 'house_vote':
    case 'senate_vote':
      return (
        <svg
          className={cls}
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M2 12 L8 4 L14 12 Z" />
          <line x1="8" y1="4" x2="8" y2="13" />
        </svg>
      );
    case 'presidential_action':
      return (
        <svg
          className={cls}
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M3 12 L3 7 L8 3 L13 7 L13 12 Z" />
          <rect x="6" y="9" width="4" height="3" />
        </svg>
      );
    case 'amendment':
      return (
        <svg
          className={cls}
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <circle cx="8" cy="8" r="3" />
          <line x1="1" y1="8" x2="5" y2="8" />
          <line x1="11" y1="8" x2="15" y2="8" />
        </svg>
      );
    default:
      return (
        <svg
          className={cls}
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <circle cx="8" cy="8" r="5.5" />
          <line x1="8" y1="6" x2="8" y2="10" />
        </svg>
      );
  }
}

// ── Kind tag ──────────────────────────────────────────────────────────────

function KindTag({
  eventType,
}: {
  eventType: TimelineEventType['event_type'];
}) {
  let label: string;
  let cls: string;

  switch (eventType) {
    case 'house_vote':
    case 'senate_vote':
      label = 'VOTE';
      cls = 'bg-blue-100 text-blue-800';
      break;
    case 'committee_referral':
      label = 'COMMITTEE';
      cls = 'bg-amber-100 text-amber-800';
      break;
    case 'presidential_action':
      label = 'EXECUTIVE';
      cls = 'bg-purple-100 text-purple-800';
      break;
    case 'introduced':
      label = 'INTRODUCED';
      cls = 'bg-emerald-100 text-emerald-800';
      break;
    case 'amendment':
      label = 'AMENDMENT';
      cls = 'bg-orange-100 text-orange-800';
      break;
    default:
      label = 'EVENT';
      cls = 'bg-gray-100 text-gray-700';
  }

  return (
    <span
      className={`mono shrink-0 rounded px-1 text-[9px] font-semibold uppercase tracking-wider ${cls}`}
    >
      {label}
    </span>
  );
}

// ── Icon circle colors ────────────────────────────────────────────────────

function iconRingClass(eventType: TimelineEventType['event_type']): string {
  switch (eventType) {
    case 'presidential_action':
      return 'border-purple-300 bg-purple-50 text-purple-700';
    case 'introduced':
      return 'border-emerald-300 bg-emerald-50 text-emerald-700';
    case 'house_vote':
    case 'senate_vote':
      return 'border-blue-300 bg-blue-50 text-blue-700';
    case 'committee_referral':
      return 'border-amber-300 bg-amber-50 text-amber-700';
    case 'amendment':
      return 'border-orange-300 bg-orange-50 text-orange-700';
    default:
      return 'border-gray-200 bg-white text-gray-500';
  }
}

function cardBorderClass(eventType: TimelineEventType['event_type']): string {
  if (eventType === 'presidential_action')
    return 'border-purple-200 bg-purple-50/30';
  return 'border-gray-200 bg-gray-50/60';
}

// ── Amendment status ──────────────────────────────────────────────────────

function AmendmentStatusBadge({
  status,
}: {
  status: AmendmentStatus | null | undefined;
}) {
  if (!status) return null;
  const configs: Record<AmendmentStatus, { label: string; cls: string }> = {
    adopted: {
      label: 'Adopted',
      cls: 'text-green-700 bg-green-50 ring-green-200',
    },
    rejected: { label: 'Rejected', cls: 'text-red-700 bg-red-50 ring-red-200' },
    withdrawn: {
      label: 'Withdrawn',
      cls: 'text-gray-600 bg-gray-50 ring-gray-200',
    },
    pending: {
      label: 'Pending',
      cls: 'text-yellow-700 bg-yellow-50 ring-yellow-200',
    },
  };
  const config = configs[status];
  if (!config) return null;
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold ring-1 ring-inset ${config.cls}`}
    >
      {config.label}
    </span>
  );
}

// ── Vote tally ────────────────────────────────────────────────────────────

function VoteTally({ event }: { event: TimelineEventType }) {
  if (event.vote_yeas == null && event.vote_nays == null) return null;
  const passed = (event.vote_yeas ?? 0) > (event.vote_nays ?? 0);
  return (
    <span
      className={`mono text-[11px] font-semibold ${passed ? 'text-emerald-700' : 'text-red-700'}`}
    >
      {event.vote_yeas}–{event.vote_nays}
      {event.vote_not_voting != null ? `–${event.vote_not_voting}` : ''}
    </span>
  );
}

// ── Signing statement blockquote ──────────────────────────────────────────

function SigningStatementQuote({ event }: { event: TimelineEventType }) {
  if (!event.signing_statement) return null;

  // Show only the first ~280 characters as an excerpt
  const MAX = 280;
  const full = event.signing_statement;
  const excerpt = full.length > MAX ? full.slice(0, MAX).trimEnd() + '…' : full;

  return (
    <blockquote className="border-primary-300 mt-2 border-l-2 bg-primary-50/40 px-3 py-2 text-sm italic text-gray-700">
      &ldquo;{excerpt}&rdquo;
      <footer className="mt-1 not-italic">
        <span className="text-[11px] text-gray-500">
          Presidential signing statement
        </span>
      </footer>
    </blockquote>
  );
}

// ── Main component ────────────────────────────────────────────────────────

/** A single entry in the legislative history Discussion panel. */
export default function TimelineEvent({ event, view }: TimelineEventProps) {
  const ring = iconRingClass(event.event_type);

  if (view === 'condensed') {
    return (
      <li className="relative flex items-center gap-3 py-1.5">
        {/* Circular icon */}
        <span
          className={`relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 ${ring}`}
        >
          <EventIcon eventType={event.event_type} />
        </span>

        <span className="mono w-20 shrink-0 text-[11px] text-gray-400">
          {formatDate(event.date)}
        </span>

        <KindTag eventType={event.event_type} />

        <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-900">
          {event.title}
        </span>

        {(event.event_type === 'house_vote' ||
          event.event_type === 'senate_vote') && <VoteTally event={event} />}
        {event.event_type === 'amendment' && (
          <AmendmentStatusBadge status={event.amendment_status} />
        )}
      </li>
    );
  }

  // Expanded pill-card
  return (
    <li className="relative flex items-start gap-3">
      {/* Circular icon */}
      <span
        className={`relative z-10 mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 ${ring}`}
      >
        <EventIcon eventType={event.event_type} />
      </span>

      {/* Card body */}
      <div
        className={`min-w-0 flex-1 rounded-lg border px-3 py-2.5 ${cardBorderClass(event.event_type)}`}
      >
        {/* Title row */}
        <div className="flex items-baseline justify-between gap-2">
          <p className="truncate text-sm font-semibold text-gray-900">
            {event.title}
          </p>
          <span className="mono shrink-0 text-[11px] text-gray-400">
            {formatDate(event.date)}
          </span>
        </div>

        {/* Tags + meta row */}
        <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
          <KindTag eventType={event.event_type} />
          {event.chamber && (
            <span className="text-[11px] text-gray-500">
              {event.chamber.toUpperCase()}
            </span>
          )}
          {(event.event_type === 'house_vote' ||
            event.event_type === 'senate_vote') && <VoteTally event={event} />}
          {event.event_type === 'amendment' && (
            <AmendmentStatusBadge status={event.amendment_status} />
          )}
        </div>

        {/* Description */}
        {event.description && (
          <p className="mt-1.5 text-sm text-gray-600">{event.description}</p>
        )}

        {/* Congressional record refs */}
        {event.congressional_record_refs.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {event.congressional_record_refs.map((ref) => (
              <span
                key={ref}
                className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-gray-500"
              >
                {ref}
              </span>
            ))}
          </div>
        )}

        {/* Signing statement inline blockquote */}
        {event.event_type === 'presidential_action' && (
          <SigningStatementQuote event={event} />
        )}
      </div>
    </li>
  );
}
