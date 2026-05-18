/** Suspense skeleton for the /laws list while ISR data is being fetched. */
export default function LawsLoading() {
  return (
    <div className="mx-auto max-w-7xl animate-pulse px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-2 h-8 w-1/4 rounded bg-gray-200" />
      <div className="mb-8 h-4 w-1/3 rounded bg-gray-200" />
      <div className="overflow-x-auto">
        <div className="mb-2 h-10 rounded bg-gray-100" />
        <div className="space-y-1">
          {Array.from({ length: 15 }).map((_, i) => (
            <div key={i} className="h-10 rounded bg-gray-50" />
          ))}
        </div>
      </div>
    </div>
  );
}
