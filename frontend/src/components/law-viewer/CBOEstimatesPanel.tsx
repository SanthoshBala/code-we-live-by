import type { CBOEstimate } from '@/lib/types';

interface CBOEstimatesPanelProps {
  estimates: CBOEstimate[];
}

const MONTH_ABBRS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

function formatPubDate(dateStr: string | null): string {
  if (!dateStr) return '';
  const [year, month] = dateStr.split('-');
  const monthIndex = parseInt(month, 10) - 1;
  const monthAbbr = MONTH_ABBRS[monthIndex] ?? month;
  return `${monthAbbr} ${year}`;
}

/** GitHub-style CI-checks panel listing CBO cost estimates for a bill. */
export default function CBOEstimatesPanel({ estimates }: CBOEstimatesPanelProps) {
  if (estimates.length === 0) return null;

  return (
    <div className="rounded-md border border-gray-200 bg-white">
      <div className="border-b border-gray-100 px-4 py-2.5">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          CBO Analysis
        </h3>
      </div>
      <div className="divide-y divide-gray-100">
        {estimates.map((est, i) => (
          <div key={i} className="px-4 py-3">
            <div className="flex items-start gap-2">
              <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-blue-500" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline gap-2">
                  <p className="text-xs font-medium text-gray-800">{est.title}</p>
                  {est.pub_date && (
                    <span className="font-mono text-[11px] text-gray-400">
                      {formatPubDate(est.pub_date)}
                    </span>
                  )}
                </div>
                {est.url && (
                  <a
                    href={est.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 inline-block text-[11px] text-blue-600 hover:underline"
                  >
                    View estimate →
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
