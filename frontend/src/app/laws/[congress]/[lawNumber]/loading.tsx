/** Suspense skeleton for the law detail page. */
export default function LawDetailLoading() {
  return (
    <div className="mx-auto max-w-7xl animate-pulse px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-1 h-7 w-3/5 rounded bg-gray-200" />
      <div className="mb-8 h-5 w-2/5 rounded bg-gray-200" />
      <div className="mb-4 flex gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-9 w-24 rounded bg-gray-100" />
        ))}
      </div>
      <div className="space-y-3">
        {Array.from({ length: 10 }).map((_, i) => (
          <div
            key={i}
            className="h-16 rounded bg-gray-100"
            style={{ opacity: 1 - i * 0.05 }}
          />
        ))}
      </div>
    </div>
  );
}
