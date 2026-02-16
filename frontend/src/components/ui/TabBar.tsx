interface Tab {
  id: string;
  label: string;
}

interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

/** Shared tab bar with primary active styling. */
export default function TabBar({ tabs, activeTab, onTabChange }: TabBarProps) {
  return (
    <div
      role="tablist"
      className="mb-4 flex border-b border-gray-200 text-sm font-medium"
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={activeTab === tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`px-4 py-2 ${activeTab === tab.id ? 'border-b-2 border-primary-600 text-primary-600' : 'text-gray-500 hover:text-gray-700'}`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
