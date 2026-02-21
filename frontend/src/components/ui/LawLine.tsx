import Link from 'next/link';

/** A law reference for enacted/amended lines. */
export interface LawReference {
  congress: number;
  lawNumber: number;
  date: string | null;
  label: string; // e.g. "PL 113-22"
  shortTitle?: string | null;
}

function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

export function formatLawDate(raw: string): string {
  // Backend may send ISO (YYYY-MM-DD) or prose ("Oct. 19, 1976") format
  const iso = /^\d{4}-\d{2}-\d{2}$/.test(raw);
  const date = new Date(iso ? raw + 'T00:00:00' : raw);
  if (isNaN(date.getTime())) return raw; // fallback to raw string
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}.${m}.${d}`;
}

/** A single row in the enacted/amended grid. */
export default function LawLine({
  label,
  law,
}: {
  label: string;
  law: LawReference;
}) {
  return (
    <>
      <dt className="text-gray-400">{label}</dt>
      <dd className="text-gray-600">
        {law.date ? formatLawDate(law.date) : '—'}
      </dd>
      <dd className="text-gray-600">{ordinal(law.congress)} Congress</dd>
      <dd className="font-mono text-gray-600">
        <Link
          href={`/laws/${law.congress}/${law.lawNumber}`}
          className="hover:text-primary-700 hover:underline"
        >
          {law.label}
        </Link>
      </dd>
      {law.shortTitle ? (
        <dd className="text-gray-500">{law.shortTitle}</dd>
      ) : (
        <dd />
      )}
    </>
  );
}
