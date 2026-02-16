import type { ItemStatus } from './types';

/** Tailwind color class for folder/file icons. Falls back to `defaultColor` when active. */
export function statusIconColor(
  status: ItemStatus,
  defaultColor: string
): string {
  switch (status) {
    case 'repealed':
      return 'text-red-500';
    case 'reserved':
      return 'text-gray-400';
    case 'transferred':
    case 'renumbered':
      return 'text-blue-500';
    case 'omitted':
      return 'text-red-500';
    default:
      return defaultColor;
  }
}

/** Badge config for a status, or null when active (no badge). */
export function statusBadge(
  status: ItemStatus
): { label: string; className: string } | null {
  switch (status) {
    case 'repealed':
      return {
        label: 'Repealed',
        className: 'bg-red-100 text-red-700',
      };
    case 'reserved':
      return {
        label: 'Reserved',
        className: 'bg-gray-100 text-gray-600',
      };
    case 'transferred':
      return {
        label: 'Transferred',
        className: 'bg-blue-100 text-blue-700',
      };
    case 'renumbered':
      return {
        label: 'Renumbered',
        className: 'bg-blue-100 text-blue-700',
      };
    case 'omitted':
      return {
        label: 'Omitted',
        className: 'bg-red-100 text-red-700',
      };
    default:
      return null;
  }
}

/** Empty-content message for a status, or generic fallback. */
export function statusMessage(status: ItemStatus): string {
  switch (status) {
    case 'repealed':
      return 'This section has been repealed.';
    case 'reserved':
      return 'This section is reserved for future use.';
    case 'transferred':
      return 'This section has been transferred.';
    case 'renumbered':
      return 'This section has been renumbered.';
    case 'omitted':
      return 'This section has been editorially omitted.';
    default:
      return 'No text content available for this section.';
  }
}

/** Detect status from a group/section name by keyword matching. */
export function detectStatus(name: string): ItemStatus {
  const hint = name.toLowerCase();
  if (/\brepealed\b/.test(hint)) return 'repealed';
  if (/\breserved\b/.test(hint)) return 'reserved';
  if (/\btransferred\b/.test(hint)) return 'transferred';
  if (/\brenumbered\b/.test(hint)) return 'renumbered';
  if (/\bomitted\b/.test(hint)) return 'omitted';
  return null;
}
