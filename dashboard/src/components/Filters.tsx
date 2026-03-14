import type { FilterState, FilterOptions } from '../types';

interface FiltersProps {
  filters: FilterState;
  options: FilterOptions;
  onToggle: (category: keyof FilterState, value: string) => void;
  onClear: () => void;
}

const CATEGORY_LABELS: Record<keyof FilterState, string> = {
  hardware: 'Hardware',
  model: 'Model',
  backend: 'Backend',
  profile: 'Profile',
};

const CATEGORY_COLORS: Record<keyof FilterState, string> = {
  hardware: '#00bcd4',
  model: '#ff9800',
  backend: '#a855f7',
  profile: '#3fb950',
};

export function Filters({ filters, options, onToggle, onClear }: FiltersProps) {
  const hasActiveFilters = Object.values(filters).some((arr) => arr.length > 0);

  return (
    <div className="mb-6 rounded-lg border border-[#21262d] bg-[#161b22] p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-medium text-[#8b949e]">Filters</span>
        {hasActiveFilters && (
          <button
            onClick={onClear}
            className="rounded px-2 py-0.5 text-xs text-[#8b949e] transition-colors hover:bg-[#21262d] hover:text-[#e6edf3]"
          >
            Clear all
          </button>
        )}
      </div>
      <div className="space-y-3">
        {(Object.keys(CATEGORY_LABELS) as Array<keyof FilterState>).map((cat) => (
          <div key={cat}>
            <div className="mb-1.5 text-xs text-[#8b949e]">{CATEGORY_LABELS[cat]}</div>
            <div className="flex flex-wrap gap-1.5">
              {options[cat].map((value) => {
                const active = filters[cat].includes(value);
                const color = CATEGORY_COLORS[cat];
                return (
                  <button
                    key={value}
                    onClick={() => onToggle(cat, value)}
                    className="rounded-md border px-2.5 py-1 text-xs font-medium transition-all"
                    style={{
                      borderColor: active ? color : '#21262d',
                      backgroundColor: active ? `${color}18` : 'transparent',
                      color: active ? color : '#8b949e',
                    }}
                  >
                    {value}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
