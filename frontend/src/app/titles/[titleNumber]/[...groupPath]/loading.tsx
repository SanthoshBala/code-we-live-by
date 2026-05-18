/** Suspense skeleton for the group directory page. */
export default function GroupDirectoryLoading() {
  return (
    <div className="animate-pulse">
      <div className="mb-2 h-7 w-2/5 rounded bg-gray-200" />
      <div className="mb-1 h-4 w-1/3 rounded bg-gray-200" />
      <div className="mb-8 h-8 w-full rounded bg-gray-100" />
      <div className="space-y-2">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="h-10 rounded bg-gray-100" />
        ))}
      </div>
    </div>
  );
}
