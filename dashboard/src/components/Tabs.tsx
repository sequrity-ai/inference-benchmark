import type { TabId } from '../types';

interface TabsProps {
  active: TabId;
  onChange: (tab: TabId) => void;
}

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'latency', label: 'Latency' },
  { id: 'throughput', label: 'Throughput' },
  { id: 'comparison', label: 'Comparison' },
  { id: 'raw', label: 'Raw Data' },
];

export function Tabs({ active, onChange }: TabsProps) {
  return (
    <div className="mb-6 flex gap-1 rounded-lg border border-[#21262d] bg-[#161b22] p-1">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`rounded-md px-4 py-2 text-sm font-medium transition-all ${
            active === tab.id
              ? 'bg-[#21262d] text-[#e6edf3]'
              : 'text-[#8b949e] hover:text-[#e6edf3]'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
