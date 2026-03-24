import type { TabId } from '../types';

interface TabsProps {
  active: TabId;
  onChange: (tab: TabId) => void;
}

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'latency', label: 'Latency' },
  { id: 'throughput', label: 'Throughput' },
  { id: 'comparison', label: 'Comparison' },
  { id: 'multi-turn', label: 'Multi-Turn' },
  { id: 'raw', label: 'Raw Data' },
];

export function Tabs({ active, onChange }: TabsProps) {
  return (
    <div className="mb-6 flex gap-0.5 rounded-lg border border-[#21262d] bg-[#0d1117] p-1">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`rounded-md px-4 py-2 text-sm font-medium transition-all ${
            active === tab.id
              ? 'bg-[#21262d] text-[#e6edf3]'
              : 'text-[#8b949e] hover:bg-[#21262d]/50 hover:text-[#c9d1d9]'
          }`}
          style={
            active === tab.id
              ? {
                  boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.07), 0 1px 3px rgba(0,0,0,0.5), inset 0 -2px 0 #00bcd4',
                }
              : {}
          }
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
