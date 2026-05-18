/** Suspense skeleton for the /titles list while ISR data is being fetched. */
export default function TitlesLoading() {
  return (
    <div className="animate-pulse">
      <div className="mb-2 h-8 w-1/3 rounded bg-gray-200" />
      <div className="mb-8 h-4 w-1/4 rounded bg-gray-200" />
      <div className="space-y-2">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="h-10 rounded bg-gray-100" />
        ))}
      </div>
    </div>
  );
}
