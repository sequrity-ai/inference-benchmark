import type { FilterState, FilterOptions } from '../types';
import { PROFILE_META, TYPE_COLORS, SOURCE_COLORS } from '../profileMeta';

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

interface MetaBadgeProps {
  label: string;
  colors: { bg: string; text: string; border: string };
}

function MetaBadge({ label, colors }: MetaBadgeProps) {
  return (
    <span
      className="inline-block rounded-full border px-1.5 py-0 text-[10px] font-medium leading-5"
      style={{ backgroundColor: colors.bg, color: colors.text, borderColor: colors.border }}
    >
      {label}
    </span>
  );
}

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
                const meta = cat === 'profile' ? PROFILE_META[value] : undefined;
                return (
                  <button
                    key={value}
                    onClick={() => onToggle(cat, value)}
                    className="flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-medium transition-all"
                    style={{
                      borderColor: active ? color : '#21262d',
                      backgroundColor: active ? `${color}18` : 'transparent',
                      color: active ? color : '#8b949e',
                    }}
                  >
                    {value}
                    {meta && (
                      <>
                        <MetaBadge label={meta.type} colors={TYPE_COLORS[meta.type]} />
                        <MetaBadge label={meta.source} colors={SOURCE_COLORS[meta.source]} />
                      </>
                    )}
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
