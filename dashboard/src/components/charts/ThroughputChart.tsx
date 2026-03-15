import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { BenchmarkResult } from '../../types';

interface ThroughputChartProps {
  seriesData: Map<string, BenchmarkResult[]>;
}

const COLORS = [
  '#00bcd4', '#ff9800', '#a855f7', '#3fb950', '#f97583',
  '#79c0ff', '#d2a8ff', '#ffa657', '#7ee787', '#ff7b72',
  '#56d4dd', '#e3b341', '#bc8cff', '#8b949e',
];

type ThroughputMetric = {
  key: string;
  label: string;
  field: keyof BenchmarkResult['summary'];
  unit: string;
};

const METRICS: ThroughputMetric[] = [
  { key: 'output_tok', label: 'Output Token Throughput', field: 'output_token_throughput', unit: 'tok/s' },
  { key: 'total_tok', label: 'Total Token Throughput', field: 'total_token_throughput', unit: 'tok/s' },
  { key: 'request', label: 'Request Throughput', field: 'request_throughput', unit: 'req/s' },
];

function buildChartData(
  seriesData: Map<string, BenchmarkResult[]>,
  field: keyof BenchmarkResult['summary']
) {
  const concSet = new Set<number>();
  const seriesNames = Array.from(seriesData.keys());

  for (const [, results] of seriesData) {
    for (const r of results) concSet.add(r.config.concurrency);
  }

  const concLevels = Array.from(concSet).sort((a, b) => a - b);

  const lookup = new Map<string, Map<number, number>>();
  for (const [key, results] of seriesData) {
    const concMap = new Map<number, number>();
    for (const r of results) concMap.set(r.config.concurrency, r.summary[field] as number);
    lookup.set(key, concMap);
  }

  return concLevels.map((conc) => {
    const point: Record<string, number> = { concurrency: conc };
    for (const name of seriesNames) {
      const val = lookup.get(name)?.get(conc);
      if (val !== undefined) point[name] = Math.round(val * 100) / 100;
    }
    return point;
  });
}

function shortenSeriesKey(key: string, allKeys: string[]): string {
  const parts = key.split(' / ');
  if (parts.length < 4) return key;

  const partSets = [new Set<string>(), new Set<string>(), new Set<string>(), new Set<string>()];
  for (const k of allKeys) {
    const p = k.split(' / ');
    p.forEach((v, i) => partSets[i]?.add(v));
  }

  const labels: string[] = [];
  const partNames = parts.map((p, i) => (i === 1 ? p.replace('Llama-3.1-', '') : p));

  for (let i = 0; i < 4; i++) {
    if (partSets[i].size > 1) labels.push(partNames[i]);
  }

  return labels.length > 0 ? labels.join(' · ') : partNames[3];
}

export function ThroughputChart({ seriesData }: ThroughputChartProps) {
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
        const chartData = buildChartData(seriesData, metric.field);

        return (
          <div
            key={metric.key}
            className="rounded-lg border border-[#21262d] bg-[#161b22] p-4"
          >
            <h3 className="mb-3 text-sm font-medium text-[#e6edf3]">
              {metric.label}
              <span className="ml-2 text-xs text-[#8b949e]">{metric.unit}</span>
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
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
                  label={{ value: metric.unit, angle: -90, position: 'insideLeft', fill: '#8b949e', fontSize: 11 }}
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
                    `${Number(value).toFixed(2)} ${metric.unit}`,
                    shortenSeriesKey(String(name), seriesNames),
                  ]}
                />
                <Legend
                  wrapperStyle={{ fontSize: '11px', color: '#8b949e' }}
                  formatter={(value: string) => shortenSeriesKey(value, seriesNames)}
                />
                {seriesNames.map((name, i) => (
                  <Area
                    key={name}
                    type="monotone"
                    dataKey={name}
                    stroke={COLORS[i % COLORS.length]}
                    fill={COLORS[i % COLORS.length]}
                    fillOpacity={0.1}
                    strokeWidth={2}
                    dot={{ r: 3, fill: COLORS[i % COLORS.length] }}
                    activeDot={{ r: 5 }}
                    connectNulls
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        );
      })}
    </div>
  );
}
