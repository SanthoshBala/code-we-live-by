import type {
  AmendmentStatus,
  TimelineEvent as TimelineEventType,
} from '@/lib/types';

interface TimelineEventProps {
  event: TimelineEventType;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  // dateStr is YYYY-MM-DD from the API
  const [year, month, day] = dateStr.split('-');
  return `${year}.${month}.${day}`;
}

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

function EventBadge({
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
      cls = 'bg-blue-50 text-blue-700 ring-blue-200';
      break;
    case 'committee_referral':
      label = 'COMMITTEE';
      cls = 'bg-amber-50 text-amber-700 ring-amber-200';
      break;
    case 'presidential_action':
      label = 'EXECUTIVE';
      cls = 'bg-purple-50 text-purple-700 ring-purple-200';
      break;
    case 'introduced':
      label = 'INTRODUCED';
      cls = 'bg-green-50 text-green-700 ring-green-200';
      break;
    case 'amendment':
      label = 'AMENDMENT';
      cls = 'bg-orange-50 text-orange-700 ring-orange-200';
      break;
    default:
      label = 'EVENT';
      cls = 'bg-gray-50 text-gray-600 ring-gray-200';
  }

  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ring-1 ring-inset ${cls}`}
    >
      {label}
    </span>
  );
}

function VoteTally({ event }: { event: TimelineEventType }) {
  if (event.vote_yeas == null && event.vote_nays == null) return null;
  const passed = (event.vote_yeas ?? 0) > (event.vote_nays ?? 0);
  return (
    <span
      className={`text-xs font-medium ${passed ? 'text-green-600' : 'text-red-600'}`}
    >
      {passed ? '✓' : '✗'} {event.vote_yeas}–{event.vote_nays}
      {event.vote_not_voting != null ? `–${event.vote_not_voting}` : ''}
    </span>
  );
}

function AmendmentStatusBadge({
  status,
}: {
  status: AmendmentStatus | null | undefined;
}) {
  if (!status) return null;

  const configs: Record<
    AmendmentStatus,
    { label: string; cls: string; prefix: string }
  > = {
    adopted: {
      label: 'Adopted',
      cls: 'text-green-700 bg-green-50 ring-green-200',
      prefix: '✓',
    },
    rejected: {
      label: 'Rejected',
      cls: 'text-red-700 bg-red-50 ring-red-200',
      prefix: '✗',
    },
    withdrawn: {
      label: 'Withdrawn',
      cls: 'text-gray-600 bg-gray-50 ring-gray-200',
      prefix: '—',
    },
    pending: {
      label: 'Pending',
      cls: 'text-yellow-700 bg-yellow-50 ring-yellow-200',
      prefix: '●',
    },
  };

  const config = configs[status];
  if (!config) return null;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold ring-1 ring-inset ${config.cls}`}
    >
      <span aria-hidden="true">{config.prefix}</span>
      {config.label}
    </span>
  );
}

/** A single row in the legislative history timeline. */
export default function TimelineEvent({ event }: TimelineEventProps) {
  const iconColor =
    event.event_type === 'presidential_action'
      ? 'text-purple-600'
      : event.event_type === 'introduced'
        ? 'text-green-600'
        : event.event_type === 'house_vote' ||
            event.event_type === 'senate_vote'
          ? 'text-blue-600'
          : event.event_type === 'committee_referral'
            ? 'text-amber-600'
            : event.event_type === 'amendment'
              ? 'text-orange-500'
              : 'text-gray-400';

  return (
    <div
      className={`flex gap-3 py-3 ${event.is_milestone ? '' : 'opacity-80'}`}
    >
      {/* Icon column */}
      <div className={`mt-0.5 ${iconColor}`}>
        <EventIcon eventType={event.event_type} />
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-gray-900">
            {event.title}
          </span>
          <EventBadge eventType={event.event_type} />
          {event.event_type === 'house_vote' ||
          event.event_type === 'senate_vote' ? (
            <VoteTally event={event} />
          ) : null}
          {event.event_type === 'amendment' ? (
            <AmendmentStatusBadge status={event.amendment_status} />
          ) : null}
        </div>

        <div className="mt-0.5 flex items-center gap-2">
          <span className="font-mono text-xs text-gray-400">
            {formatDate(event.date)}
          </span>
          {event.chamber && (
            <span className="text-xs text-gray-400">
              {event.chamber.toUpperCase()}
            </span>
          )}
        </div>

        {event.description && (
          <p className="mt-1 text-xs leading-relaxed text-gray-600">
            {event.description}
          </p>
        )}

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
      </div>
    </div>
  );
}
