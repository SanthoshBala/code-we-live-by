/** Document icon representing a code section (page with folded corner). */
export default function FileIcon({ muted = false }: { muted?: boolean } = {}) {
  const color = muted ? 'text-gray-300' : 'text-gray-400';
  return (
    <svg
      className={`h-4 w-4 shrink-0 ${color}`}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
        clipRule="evenodd"
      />
    </svg>
  );
}
