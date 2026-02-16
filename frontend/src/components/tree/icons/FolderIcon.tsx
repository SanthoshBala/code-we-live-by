/** Folder icon that switches between open and closed states. */
export default function FolderIcon({
  open,
  muted = false,
}: {
  open: boolean;
  muted?: boolean;
}) {
  const color = muted ? 'text-gray-300' : 'text-amber-500';
  return open ? (
    <svg
      className={`h-4 w-4 shrink-0 ${color}`}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v1H2V6z" />
      <path
        fillRule="evenodd"
        d="M2 9h16v5a2 2 0 01-2 2H4a2 2 0 01-2-2V9z"
        clipRule="evenodd"
      />
    </svg>
  ) : (
    <svg
      className={`h-4 w-4 shrink-0 ${color}`}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
    </svg>
  );
}
