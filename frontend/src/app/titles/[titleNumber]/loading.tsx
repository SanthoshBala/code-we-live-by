/** Suspense skeleton for the title directory page. */
export default function TitleDirectoryLoading() {
  return (
    <div className="animate-pulse">
      <div className="mb-2 h-7 w-2/5 rounded bg-gray-200" />
      <div className="mb-1 h-4 w-1/4 rounded bg-gray-200" />
      <div className="mb-8 h-8 w-full rounded bg-gray-100" />
      <div className="space-y-2">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="h-10 rounded bg-gray-100" />
        ))}
      </div>
    </div>
  );
}
