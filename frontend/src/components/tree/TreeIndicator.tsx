import FolderIcon from './icons/FolderIcon';

/** Expand/collapse indicator using folder open/closed icon. */
export default function TreeIndicator({ expanded }: { expanded: boolean }) {
  return <FolderIcon open={expanded} />;
}
