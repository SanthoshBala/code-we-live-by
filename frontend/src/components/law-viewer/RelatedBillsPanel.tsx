import Link from 'next/link';
import type { RelatedBill } from '@/lib/types';

interface RelatedBillsPanelProps {
  bills: RelatedBill[];
}

const BILL_TYPE_LABELS: Record<string, string> = {
  hr: 'H.R.',
  s: 'S.',
  hjres: 'H.J.Res.',
  sjres: 'S.J.Res.',
  hconres: 'H.Con.Res.',
  sconres: 'S.Con.Res.',
  hres: 'H.Res.',
  sres: 'S.Res.',
};

const BILL_TYPE_PATHS: Record<string, string> = {
  hr: 'house-bill',
  s: 'senate-bill',
  hjres: 'house-joint-resolution',
  sjres: 'senate-joint-resolution',
  hconres: 'house-concurrent-resolution',
  sconres: 'senate-concurrent-resolution',
  hres: 'house-simple-resolution',
  sres: 'senate-simple-resolution',
};

function formatBillLabel(bill: RelatedBill): string {
  const key = bill.bill_type.toLowerCase();
  const typeLabel = BILL_TYPE_LABELS[key] ?? bill.bill_type.toUpperCase();
  return `${typeLabel} ${bill.bill_number} (${bill.congress}th)`;
}

function congressGovUrl(bill: RelatedBill): string {
  const key = bill.bill_type.toLowerCase();
  const typePath = BILL_TYPE_PATHS[key] ?? key;
  return `https://www.congress.gov/bill/${bill.congress}th-congress/${typePath}/${bill.bill_number}`;
}

/** Linked-PRs-style sidebar panel listing bills related to this legislation. */
export default function RelatedBillsPanel({ bills }: RelatedBillsPanelProps) {
  if (bills.length === 0) return null;

  return (
    <div className="rounded-md border border-gray-200 bg-white">
      <div className="border-b border-gray-100 px-4 py-2.5">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          Related Bills
        </h3>
      </div>
      <div className="divide-y divide-gray-100">
        {bills.map((bill, i) => (
          <div key={i} className="px-4 py-3">
            <div className="flex items-start gap-2">
              {/* pull-request icon */}
              <svg
                className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-400"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <circle cx="4" cy="4" r="2" />
                <circle cx="12" cy="12" r="2" />
                <circle cx="12" cy="4" r="2" />
                <line x1="4" y1="6" x2="4" y2="10" />
                <path d="M12 6 L12 9 Q12 10 11 10 L5 10" />
              </svg>
              <div className="min-w-0 flex-1">
                {bill.law_number != null ? (
                  <Link
                    href={`/laws/${bill.congress}/${bill.law_number}`}
                    className="text-xs font-medium text-blue-600 hover:underline"
                  >
                    {formatBillLabel(bill)}
                  </Link>
                ) : (
                  <a
                    href={congressGovUrl(bill)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-medium text-blue-600 hover:underline"
                  >
                    {formatBillLabel(bill)}
                  </a>
                )}
                {bill.title && (
                  <p className="mt-0.5 text-[11px] leading-relaxed text-gray-500">
                    {bill.title}
                  </p>
                )}
                {bill.relationship_details && (
                  <p className="mt-0.5 text-[11px] italic text-gray-400">
                    {bill.relationship_details}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
