'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';

interface TreeDisplaySettings {
  showTreeLines: boolean;
  showBreadcrumb: boolean;
}

interface TreeDisplayContextValue {
  settings: TreeDisplaySettings;
  toggleTreeLines: () => void;
  toggleBreadcrumb: () => void;
}

const STORAGE_KEY = 'cwlb-tree-display';

const defaults: TreeDisplaySettings = {
  showTreeLines: false,
  showBreadcrumb: false,
};

const TreeDisplayContext = createContext<TreeDisplayContextValue>({
  settings: defaults,
  toggleTreeLines: () => {},
  toggleBreadcrumb: () => {},
});

export function TreeDisplayProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [settings, setSettings] = useState<TreeDisplaySettings>(defaults);

  // Load persisted settings on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setSettings({ ...defaults, ...JSON.parse(stored) });
      }
    } catch {
      // Ignore parse errors
    }
  }, []);

  // Persist on change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // Ignore quota errors
    }
  }, [settings]);

  const toggleTreeLines = useCallback(() => {
    setSettings((prev) => ({ ...prev, showTreeLines: !prev.showTreeLines }));
  }, []);

  const toggleBreadcrumb = useCallback(() => {
    setSettings((prev) => ({ ...prev, showBreadcrumb: !prev.showBreadcrumb }));
  }, []);

  return (
    <TreeDisplayContext.Provider
      value={{ settings, toggleTreeLines, toggleBreadcrumb }}
    >
      {children}
    </TreeDisplayContext.Provider>
  );
}

export function useTreeDisplay() {
  return useContext(TreeDisplayContext);
}
