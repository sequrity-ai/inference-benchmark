import type { BenchmarkResult } from '../types';

interface KPICardsProps {
  data: BenchmarkResult[];
  allData: BenchmarkResult[];
}

export function KPICards({ data, allData }: KPICardsProps) {
  const totalRuns = data.length;
  const hwConfigs = new Set(data.map((r) => r.hardware)).size;
  const models = new Set(data.map((r) => r.modelShort)).size;

  const medianThroughput =
    data.length > 0
      ? (() => {
          const vals = data
            .map((r) => r.summary.output_token_throughput)
            .filter((v) => v > 0)
            .sort((a, b) => a - b);
          if (vals.length === 0) return 0;
          const mid = Math.floor(vals.length / 2);
          return vals.length % 2 === 0 ? (vals[mid - 1] + vals[mid]) / 2 : vals[mid];
        })()
      : 0;

  const isFiltered = data.length !== allData.length;

  const cards = [
    {
      label: 'Total Runs',
      value: totalRuns,
      suffix: isFiltered ? ` / ${allData.length}` : '',
      accent: '#00bcd4',
    },
    {
      label: 'Hardware Configs',
      value: hwConfigs,
      suffix: '',
      accent: '#ff9800',
    },
    {
      label: 'Models Tested',
      value: models,
      suffix: '',
      accent: '#a855f7',
    },
    {
      label: 'Median Out Tok/s',
      value: medianThroughput.toFixed(1),
      suffix: '',
      accent: '#3fb950',
    },
  ];

  return (
    <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-lg border border-[#21262d] bg-[#161b22] p-4"
          style={{ borderTopColor: card.accent, borderTopWidth: '2px' }}
        >
          <div className="mb-1 text-xs text-[#8b949e]">{card.label}</div>
          <div className="font-mono text-2xl font-semibold tracking-tight">
            {card.value}
            {card.suffix && (
              <span className="text-sm text-[#8b949e]">{card.suffix}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
