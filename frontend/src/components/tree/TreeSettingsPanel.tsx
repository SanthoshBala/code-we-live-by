import { useTreeDisplay } from '@/contexts/TreeDisplayContext';

/** Small settings bar with toggles for tree display options. */
export default function TreeSettingsPanel() {
  const { settings, toggleTreeLines, toggleBreadcrumb } = useTreeDisplay();

  return (
    <div className="mb-2 flex items-center gap-4 text-xs text-gray-500">
      <label className="flex cursor-pointer items-center gap-1">
        <input
          type="checkbox"
          checked={settings.showTreeLines}
          onChange={toggleTreeLines}
          className="accent-primary-600"
        />
        Connector lines
      </label>
      <label className="flex cursor-pointer items-center gap-1">
        <input
          type="checkbox"
          checked={settings.showBreadcrumb}
          onChange={toggleBreadcrumb}
          className="accent-primary-600"
        />
        Path breadcrumb
      </label>
    </div>
  );
}
