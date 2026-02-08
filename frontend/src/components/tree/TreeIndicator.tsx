import FolderIcon from './icons/FolderIcon';

interface TreeIndicatorProps {
  expanded: boolean;
  onToggle?: (e: React.MouseEvent) => void;
}

/** Expand/collapse indicator using folder open/closed icon. */
export default function TreeIndicator({
  expanded,
  onToggle,
}: TreeIndicatorProps) {
  if (onToggle) {
    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          e.preventDefault();
          onToggle(e);
        }}
        className="flex h-6 w-6 shrink-0 items-center justify-center rounded hover:bg-gray-200"
        aria-label={expanded ? 'Collapse' : 'Expand'}
      >
        <FolderIcon open={expanded} />
      </button>
    );
  }
  return <FolderIcon open={expanded} />;
}
