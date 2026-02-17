import type { ItemStatus } from '@/lib/types';
import FolderIcon from './icons/FolderIcon';

interface TreeIndicatorProps {
  expanded: boolean;
  onToggle?: (e: React.MouseEvent) => void;
  status?: ItemStatus;
}

/** Expand/collapse indicator using folder open/closed icon. */
export default function TreeIndicator({
  expanded,
  onToggle,
  status,
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
        <FolderIcon open={expanded} status={status} />
      </button>
    );
  }
  return <FolderIcon open={expanded} status={status} />;
}
