import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { BenchmarkResult } from '../../types';

interface LatencyChartProps {
  seriesData: Map<string, BenchmarkResult[]>;
}

const COLORS = [
  '#00bcd4', '#ff9800', '#a855f7', '#3fb950', '#f97583',
  '#79c0ff', '#d2a8ff', '#ffa657', '#7ee787', '#ff7b72',
  '#56d4dd', '#e3b341', '#bc8cff', '#8b949e',
];

type LatencyMetric = {
  key: string;
  label: string;
  medianField: keyof BenchmarkResult['summary'];
  p90Field: keyof BenchmarkResult['summary'];
  p99Field: keyof BenchmarkResult['summary'];
};

const METRICS: LatencyMetric[] = [
  {
    key: 'ttft',
    label: 'Time to First Token (TTFT)',
    medianField: 'median_ttft_ms',
    p90Field: 'p90_ttft_ms',
    p99Field: 'p99_ttft_ms',
  },
  {
    key: 'tpot',
    label: 'Time per Output Token (TPOT)',
    medianField: 'median_tpot_ms',
    p90Field: 'p90_tpot_ms',
    p99Field: 'p99_tpot_ms',
  },
  {
    key: 'e2el',
    label: 'End-to-End Latency (E2EL)',
    medianField: 'median_e2el_ms',
    p90Field: 'p90_e2el_ms',
    p99Field: 'p99_e2el_ms',
  },
];

function buildChartData(
  seriesData: Map<string, BenchmarkResult[]>,
  medianField: keyof BenchmarkResult['summary']
) {
  // Collect all concurrency levels
  const concSet = new Set<number>();
  const seriesNames = Array.from(seriesData.keys());

  for (const [, results] of seriesData) {
    for (const r of results) {
      concSet.add(r.config.concurrency);
    }
  }

  const concLevels = Array.from(concSet).sort((a, b) => a - b);

  // Build lookup: seriesKey -> concurrency -> value
  const lookup = new Map<string, Map<number, number>>();
  for (const [key, results] of seriesData) {
    const concMap = new Map<number, number>();
    for (const r of results) {
      concMap.set(r.config.concurrency, r.summary[medianField] as number);
    }
    lookup.set(key, concMap);
  }

  return concLevels.map((conc) => {
    const point: Record<string, number> = { concurrency: conc };
    for (const name of seriesNames) {
      const val = lookup.get(name)?.get(conc);
      if (val !== undefined) {
        point[name] = Math.round(val * 100) / 100;
      }
    }
    return point;
  });
}

function shortenSeriesKey(key: string): string {
  // "H100 / Llama-3.1-70B FP8 / vllm / output-short" -> "H100 70B vllm output-short"
  const parts = key.split(' / ');
  if (parts.length < 4) return key;
  const hw = parts[0];
  const modelQuant = parts[1].replace('Llama-3.1-', '').replace('Llama-3.1-', '');
  const backend = parts[2];
  const profile = parts[3];
  return `${hw} ${modelQuant} ${backend} ${profile}`;
}

export function LatencyChart({ seriesData }: LatencyChartProps) {
  if (seriesData.size === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-[#21262d] bg-[#161b22] text-[#8b949e]">
        No data matches current filters
      </div>
    );
  }

  const seriesNames = Array.from(seriesData.keys());

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {METRICS.map((metric) => {
        const chartData = buildChartData(seriesData, metric.medianField);

        return (
          <div
            key={metric.key}
            className="rounded-lg border border-[#21262d] bg-[#161b22] p-4"
          >
            <h3 className="mb-3 text-sm font-medium text-[#e6edf3]">
              {metric.label}
              <span className="ml-2 text-xs text-[#8b949e]">median, ms</span>
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                <XAxis
                  dataKey="concurrency"
                  scale="log"
                  domain={['dataMin', 'dataMax']}
                  type="number"
                  tick={{ fill: '#8b949e', fontSize: 11 }}
                  axisLine={{ stroke: '#21262d' }}
                  tickLine={{ stroke: '#21262d' }}
                  label={{ value: 'Concurrency', position: 'insideBottom', offset: -2, fill: '#8b949e', fontSize: 11 }}
                />
                <YAxis
                  tick={{ fill: '#8b949e', fontSize: 11 }}
                  axisLine={{ stroke: '#21262d' }}
                  tickLine={{ stroke: '#21262d' }}
                  label={{ value: 'ms', angle: -90, position: 'insideLeft', fill: '#8b949e', fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#161b22',
                    border: '1px solid #21262d',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#e6edf3',
                  }}
                  labelFormatter={(v) => `Concurrency: ${v}`}
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  formatter={(value: any, name: any) => [
                    `${Number(value).toFixed(2)} ms`,
                    shortenSeriesKey(String(name)),
                  ]}
                />
                <Legend
                  wrapperStyle={{ fontSize: '11px', color: '#8b949e' }}
                  formatter={(value: string) => shortenSeriesKey(value)}
                />
                {seriesNames.map((name, i) => (
                  <Line
                    key={name}
                    type="monotone"
                    dataKey={name}
                    stroke={COLORS[i % COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 3, fill: COLORS[i % COLORS.length] }}
                    activeDot={{ r: 5 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        );
      })}
    </div>
  );
}
