import type { ChamberVote } from '@/lib/types';

interface VotesSidebarProps {
  votes: ChamberVote[];
}

function PassIcon() {
  return (
    <svg
      className="h-3.5 w-3.5 text-green-600"
      viewBox="0 0 14 14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <polyline points="2,7 6,11 12,3" />
    </svg>
  );
}

function FailIcon() {
  return (
    <svg
      className="h-3.5 w-3.5 text-red-600"
      viewBox="0 0 14 14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <line x1="3" y1="3" x2="11" y2="11" />
      <line x1="11" y1="3" x2="3" y2="11" />
    </svg>
  );
}

function VoteBar({
  yeas,
  nays,
  notVoting,
}: {
  yeas: number;
  nays: number;
  notVoting: number;
}) {
  const total = yeas + nays + notVoting;
  if (total === 0) return null;
  const yeaPct = (yeas / total) * 100;
  const nayPct = (nays / total) * 100;
  return (
    <div className="mt-1.5 flex h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
      <div className="bg-green-500" style={{ width: `${yeaPct}%` }} />
      <div className="bg-red-500" style={{ width: `${nayPct}%` }} />
    </div>
  );
}

/** Right-panel vote summary: one row per chamber with yea/nay/abstain counts. */
export default function VotesSidebar({ votes }: VotesSidebarProps) {
  if (votes.length === 0) return null;

  return (
    <div className="rounded-md border border-gray-200 bg-white px-4 py-3">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Passage Votes
      </h3>

      <div className="space-y-3">
        {votes.map((v) => {
          const passed = v.yeas > v.nays;
          return (
            <div key={v.chamber}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  {passed ? <PassIcon /> : <FailIcon />}
                  <span className="text-xs font-semibold uppercase tracking-wide text-gray-700">
                    {v.chamber}
                  </span>
                </div>
                <span
                  className={`text-xs font-medium ${passed ? 'text-green-600' : 'text-red-600'}`}
                >
                  {passed ? 'Passed' : 'Failed'}
                </span>
              </div>
              <VoteBar yeas={v.yeas} nays={v.nays} notVoting={v.not_voting} />
              <div className="mt-1 flex gap-3 text-[11px] text-gray-500">
                <span>
                  <span className="font-medium text-green-700">{v.yeas}</span>{' '}
                  yeas
                </span>
                <span>
                  <span className="font-medium text-red-700">{v.nays}</span>{' '}
                  nays
                </span>
                {v.not_voting > 0 && (
                  <span>
                    <span className="font-medium text-gray-700">
                      {v.not_voting}
                    </span>{' '}
                    not voting
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
