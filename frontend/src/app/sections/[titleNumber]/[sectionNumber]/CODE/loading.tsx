/** Suspense skeleton for the section CODE viewer page. */
export default function SectionCodeLoading() {
  return (
    <div className="animate-pulse">
      <div className="mb-2 h-7 w-2/5 rounded bg-gray-200" />
      <div className="mb-1 h-4 w-1/3 rounded bg-gray-200" />
      <div className="mb-6 h-8 w-full rounded bg-gray-100" />
      <div className="space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="h-4 rounded bg-gray-100"
            style={{ width: `${70 + (i % 3) * 10}%` }}
          />
        ))}
      </div>
      <div className="mt-6 space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-4 rounded bg-gray-100"
            style={{ width: `${60 + (i % 4) * 8}%` }}
          />
        ))}
      </div>
    </div>
  );
}
