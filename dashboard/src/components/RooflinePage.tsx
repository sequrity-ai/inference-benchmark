import { useState, useEffect, useMemo, Component, type ReactNode } from 'react';
import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
  ReferenceLine,
} from 'recharts';
import type { RooflineData, RooflineEntry, RooflineKernel } from '../types-roofline';

// ── Hardware roofline ceilings (H100 SXM5 BF16) ──────────────────────────────
const PEAK_COMPUTE_TFLOPS = 989; // BF16 tensor core peak
const PEAK_MEMORY_BW_TB = 3.35;  // TB/s  →  TFLOPS = AI * 3.35
const RIDGE_POINT_AI = PEAK_COMPUTE_TFLOPS / PEAK_MEMORY_BW_TB; // ≈295

// ── Category colors (colorblind-safe Wong palette) ───────────────────────────
const CATEGORY_COLORS: Record<string, string> = {
  gemm:         '#0072B2',
  attention:    '#E69F00',
  elementwise:  '#666666',
  memory:       '#BBBBBB',
  activation:   '#CC79A7',
  reduce:       '#009E73',
  rope:         '#D55E00',
  'moe-routing':'#F0E442',
  indexing:     '#999999',
  other:        '#444444',
};

const CATEGORY_ORDER = [
  'gemm', 'attention', 'activation', 'reduce', 'rope',
  'elementwise', 'memory', 'indexing', 'moe-routing', 'other',
];

function categoryColor(cat: string): string {
  return CATEGORY_COLORS[cat] ?? CATEGORY_COLORS['other'];
}

// ── Build roofline ceiling as a series of [AI, TFLOPS] points on log scale ───
function buildRooflineCeiling(): Array<{ ai: number; tflops: number }> {
  // Memory-bound slope: TFLOPS = BW * AI, from AI=0.1 up to ridge point
  // Compute-bound flat: TFLOPS = PEAK, from ridge point to AI=10000
  const memPoints: Array<{ ai: number; tflops: number }> = [];
  // Use enough log-spaced points for a smooth line on log-log scale
  const logStart = Math.log10(0.1);
  const logRidge = Math.log10(RIDGE_POINT_AI);
  const steps = 40;
  for (let i = 0; i <= steps; i++) {
    const logAI = logStart + (i / steps) * (logRidge - logStart);
    const ai = Math.pow(10, logAI);
    memPoints.push({ ai, tflops: PEAK_MEMORY_BW_TB * ai });
  }
  // Flat compute ceiling
  const computePoints: Array<{ ai: number; tflops: number }> = [
    { ai: RIDGE_POINT_AI, tflops: PEAK_COMPUTE_TFLOPS },
    { ai: 10000, tflops: PEAK_COMPUTE_TFLOPS },
  ];
  return [...memPoints, ...computePoints];
}

const ROOFLINE_CEILING = buildRooflineCeiling();

// ── Error boundary to prevent white-page crashes from Recharts ────────────────
interface EBProps { children: ReactNode; fallback?: ReactNode }
interface EBState { hasError: boolean; error?: Error }
class ChartErrorBoundary extends Component<EBProps, EBState> {
  state: EBState = { hasError: false };
  static getDerivedStateFromError(error: Error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="flex h-64 items-center justify-center rounded-lg border border-red-800 bg-red-900/20 text-red-400">
          <div className="text-center">
            <div className="text-sm font-semibold">Chart rendering error</div>
            <div className="mt-1 text-xs opacity-70">{this.state.error?.message}</div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ── Log tick formatter ────────────────────────────────────────────────────────
function logTick(value: number): string {
  if (value >= 1000) return `${(value / 1000).toFixed(0)}k`;
  if (value >= 1) return `${value}`;
  return `${value}`;
}

// ── Shorten kernel name for tooltip ──────────────────────────────────────────
function shortKernelName(name: string | undefined): string {
  if (!name) return '(unknown)';
  // If it's an aten:: op, use that
  const aten = name.match(/^(aten::\w+)/);
  if (aten) return aten[1];
  // If it's a void kernel, extract meaningful part
  const voidMatch = name.match(/void\s+[\w:]+::([\w_]+)</);
  if (voidMatch) return voidMatch[1];
  // Fallback: truncate
  return name.length > 60 ? name.slice(0, 57) + '…' : name;
}

// ── Custom scatter dot with category color ────────────────────────────────────
interface DotProps {
  cx?: number;
  cy?: number;
  payload?: RooflineKernel;
}

function KernelDot({ cx = 0, cy = 0, payload }: DotProps) {
  if (!payload) return null;
  // Guard against NaN from log scale computation
  if (!Number.isFinite(cx) || !Number.isFinite(cy)) return null;
  const color = categoryColor(payload.category);
  return (
    <circle
      cx={cx}
      cy={cy}
      r={5}
      fill={color}
      fillOpacity={0.85}
      stroke={color}
      strokeWidth={1}
      strokeOpacity={0.4}
    />
  );
}

// ── Custom tooltip for scatter ────────────────────────────────────────────────
interface ScatterTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: RooflineKernel }>;
}

function ScatterTooltip({ active, payload }: ScatterTooltipProps) {
  if (!active || !payload?.length) return null;
  const k = payload[0]?.payload;
  if (!k) return null;
  return (
    <div
      style={{
        backgroundColor: '#161b22',
        border: '1px solid #30363d',
        borderRadius: '8px',
        padding: '10px 14px',
        fontSize: '12px',
        color: '#e6edf3',
        boxShadow: '0 4px 16px rgba(0,0,0,0.6)',
        maxWidth: '320px',
      }}
    >
      <div
        style={{
          marginBottom: 6,
          fontWeight: 600,
          color: categoryColor(k.category),
          wordBreak: 'break-all',
          lineHeight: 1.4,
        }}
      >
        {shortKernelName(k.name)}
      </div>
      <div style={{ color: '#8b949e', marginBottom: 4 }}>
        <span
          style={{
            display: 'inline-block',
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: categoryColor(k.category),
            marginRight: 5,
          }}
        />
        {k.category}
      </div>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <tbody>
          <tr>
            <td style={{ color: '#8b949e', paddingRight: 12 }}>Arith. Intensity</td>
            <td style={{ fontFamily: 'monospace', color: '#e6edf3' }}>
              {(k.arithmetic_intensity ?? 0).toFixed(1)} FLOP/B
            </td>
          </tr>
          <tr>
            <td style={{ color: '#8b949e', paddingRight: 12 }}>Achieved TFLOPS</td>
            <td style={{ fontFamily: 'monospace', color: '#e6edf3' }}>
              {(k.achieved_tflops ?? 0).toFixed(2)}
            </td>
          </tr>
          <tr>
            <td style={{ color: '#8b949e', paddingRight: 12 }}>CUDA time</td>
            <td style={{ fontFamily: 'monospace', color: '#e6edf3' }}>
              {(k.cuda_time_us ?? 0).toFixed(1)} µs
            </td>
          </tr>
          <tr>
            <td style={{ color: '#8b949e', paddingRight: 12 }}>Calls</td>
            <td style={{ fontFamily: 'monospace', color: '#e6edf3' }}>{k.calls}</td>
          </tr>
          <tr>
            <td style={{ color: '#8b949e', paddingRight: 12 }}>Batch size</td>
            <td style={{ fontFamily: 'monospace', color: '#e6edf3' }}>{k.batch_size}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// ── Stacked bar chart tooltip ─────────────────────────────────────────────────
interface BarTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; fill: string }>;
  label?: string;
}

function BarTooltip({ active, payload, label }: BarTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        backgroundColor: '#161b22',
        border: '1px solid #30363d',
        borderRadius: '8px',
        padding: '10px 14px',
        fontSize: '12px',
        color: '#e6edf3',
        boxShadow: '0 4px 16px rgba(0,0,0,0.6)',
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8, color: '#c9d1d9' }}>
        Batch size {label}
      </div>
      {[...payload].reverse().map((entry) => (
        <div
          key={entry.name}
          style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 2 }}
        >
          <span style={{ color: '#8b949e', display: 'flex', alignItems: 'center', gap: 5 }}>
            <span
              style={{
                display: 'inline-block',
                width: 8,
                height: 8,
                borderRadius: 2,
                backgroundColor: entry.fill,
              }}
            />
            {entry.name}
          </span>
          <span style={{ fontFamily: 'monospace', color: '#e6edf3' }}>
            {(entry.value ?? 0).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Stats card ────────────────────────────────────────────────────────────────
interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  accent: string;
}

function StatCard({ label, value, sub, accent }: StatCardProps) {
  return (
    <div
      className="rounded-lg border border-[#21262d] bg-[#161b22] p-4"
      style={{ borderTopColor: accent, borderTopWidth: '3px' }}
    >
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-[#8b949e]">
        {label}
      </div>
      <div className="font-mono text-2xl font-bold tracking-tight text-[#e6edf3]">{value}</div>
      {sub && <div className="mt-1 text-xs text-[#8b949e]">{sub}</div>}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function RooflinePage() {
  const [rooflineData, setRooflineData] = useState<RooflineData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [selectedPhase, setSelectedPhase] = useState<'prefill' | 'decode'>('prefill');
  const [selectedBatches, setSelectedBatches] = useState<Set<number>>(new Set([1, 4, 8, 32, 64]));

  // Load data
  useEffect(() => {
    fetch('./roofline-data.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<RooflineData>;
      })
      .then((d) => {
        setRooflineData(d);
        if (d.models.length > 0) setSelectedModel(d.models[0]);
        setSelectedBatches(new Set(d.batch_sizes));
      })
      .catch((e: Error) => setLoadError(e.message));
  }, []);

  // Filtered entries
  const filteredEntries = useMemo<RooflineEntry[]>(() => {
    if (!rooflineData) return [];
    return rooflineData.entries.filter(
      (e) =>
        e.model === selectedModel &&
        e.phase === selectedPhase &&
        selectedBatches.has(e.batch_size)
    );
  }, [rooflineData, selectedModel, selectedPhase, selectedBatches]);

  // All kernels from filtered entries
  const allKernels = useMemo<RooflineKernel[]>(() => {
    return filteredEntries.flatMap((e) => e.kernels);
  }, [filteredEntries]);

  // Kernels mapped to axis-compatible field names for Recharts scatter
  // XAxis dataKey="ai", YAxis dataKey="tflops" — must match field names in data objects
  const scatterKernels = useMemo(() => {
    return allKernels
      .filter((k) => k.arithmetic_intensity > 0 && k.achieved_tflops > 0
        && Number.isFinite(k.arithmetic_intensity) && Number.isFinite(k.achieved_tflops))
      .map((k) => ({
        ...k,
        ai: k.arithmetic_intensity,
        tflops: k.achieved_tflops,
      }));
  }, [allKernels]);

  // Stats
  const stats = useMemo(() => {
    if (allKernels.length === 0) return null;
    const totalTime = allKernels.reduce((s, k) => s + k.cuda_time_us, 0);
    const gemmTime = allKernels
      .filter((k) => k.category === 'gemm')
      .reduce((s, k) => s + k.cuda_time_us, 0);
    const gemmPct = totalTime > 0 ? (gemmTime / totalTime) * 100 : 0;

    const gemmKernels = allKernels.filter((k) => k.category === 'gemm');
    const topGemmTflops =
      gemmKernels.length > 0 ? Math.max(...gemmKernels.map((k) => k.achieved_tflops)) : 0;

    const computeBound = allKernels.filter(
      (k) => k.arithmetic_intensity >= RIDGE_POINT_AI
    ).length;
    const memBound = allKernels.filter(
      (k) => k.arithmetic_intensity < RIDGE_POINT_AI
    ).length;

    return { totalTime, gemmPct, topGemmTflops, computeBound, memBound };
  }, [allKernels]);

  // Stacked bar data: time % per category per batch size
  const barData = useMemo(() => {
    if (filteredEntries.length === 0) return [];
    return filteredEntries
      .sort((a, b) => a.batch_size - b.batch_size)
      .map((entry) => {
        const row: Record<string, number | string> = { batch_size: entry.batch_size };
        for (const s of entry.category_summary) {
          row[s.category] = Math.round(s.duration_pct * 10) / 10;
        }
        return row;
      });
  }, [filteredEntries]);

  // Present categories in this data
  const presentCategories = useMemo(() => {
    const cats = new Set<string>();
    for (const entry of filteredEntries) {
      for (const s of entry.category_summary) {
        if (s.duration_pct > 0) cats.add(s.category);
      }
    }
    return CATEGORY_ORDER.filter((c) => cats.has(c));
  }, [filteredEntries]);

  const toggleBatch = (bs: number) => {
    setSelectedBatches((prev) => {
      const next = new Set(prev);
      if (next.has(bs)) {
        if (next.size > 1) next.delete(bs);
      } else {
        next.add(bs);
      }
      return next;
    });
  };

  // ── Render ────────────────────────────────────────────────────────────────
  if (loadError) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-[#f97583]/30 bg-[#f97583]/10 text-[#f97583]">
        <div className="text-center">
          <div className="mb-2 text-lg font-semibold">Failed to load roofline data</div>
          <div className="text-sm">{loadError}</div>
          <div className="mt-2 text-xs text-[#8b949e]">
            Run{' '}
            <code className="rounded bg-[#21262d] px-1">
              npx tsx scripts/build-roofline-data.ts
            </code>{' '}
            to generate roofline-data.json
          </div>
        </div>
      </div>
    );
  }

  if (!rooflineData) {
    return (
      <div className="flex h-64 items-center justify-center text-[#8b949e]">
        Loading roofline data...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Controls ────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[#21262d] bg-[#161b22] px-4 py-3">
        {/* Model selector */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-[#8b949e]">
            Model
          </span>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="rounded border border-[#30363d] bg-[#0d1117] px-3 py-1.5 text-sm text-[#e6edf3] focus:border-[#00bcd4] focus:outline-none"
          >
            {rooflineData.models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div className="h-5 w-px bg-[#30363d]" />

        {/* Phase toggle */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-[#8b949e]">
            Phase
          </span>
          <div className="flex rounded border border-[#30363d] bg-[#0d1117] overflow-hidden">
            {(['prefill', 'decode'] as const).map((phase) => (
              <button
                key={phase}
                onClick={() => setSelectedPhase(phase)}
                className={`px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
                  selectedPhase === phase
                    ? 'bg-[#00bcd4]/15 text-[#00bcd4]'
                    : 'text-[#8b949e] hover:text-[#c9d1d9]'
                }`}
              >
                {phase}
              </button>
            ))}
          </div>
        </div>

        <div className="h-5 w-px bg-[#30363d]" />

        {/* Batch size multi-select */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-[#8b949e]">
            Batch
          </span>
          <div className="flex gap-1">
            {rooflineData.batch_sizes.map((bs) => (
              <button
                key={bs}
                onClick={() => toggleBatch(bs)}
                className={`rounded border px-2.5 py-1 text-xs font-mono font-semibold transition-colors ${
                  selectedBatches.has(bs)
                    ? 'border-[#00bcd4]/50 bg-[#00bcd4]/10 text-[#00bcd4]'
                    : 'border-[#30363d] bg-transparent text-[#8b949e] hover:border-[#484f58] hover:text-[#c9d1d9]'
                }`}
              >
                {bs}
              </button>
            ))}
          </div>
        </div>

        <div className="ml-auto text-xs text-[#8b949e]">
          {allKernels.length} kernels
        </div>
      </div>

      {/* ── Stats cards ─────────────────────────────────────────────────── */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard
            label="Total CUDA Time"
            value={
              stats.totalTime >= 1000
                ? `${(stats.totalTime / 1000).toFixed(1)} ms`
                : `${stats.totalTime.toFixed(0)} µs`
            }
            sub="across filtered kernels"
            accent="#00bcd4"
          />
          <StatCard
            label="GEMM % of Time"
            value={`${stats.gemmPct.toFixed(1)}%`}
            sub="matrix multiplications"
            accent="#0072B2"
          />
          <StatCard
            label="Peak GEMM TFLOPS"
            value={`${stats.topGemmTflops.toFixed(0)}`}
            sub={`of ${PEAK_COMPUTE_TFLOPS} theoretical`}
            accent="#E69F00"
          />
          <StatCard
            label="Compute / Mem Bound"
            value={`${stats.computeBound} / ${stats.memBound}`}
            sub={`ridge at AI ≈ ${RIDGE_POINT_AI.toFixed(0)}`}
            accent="#3fb950"
          />
        </div>
      )}

      {/* ── Roofline chart ───────────────────────────────────────────────── */}
      <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-[#e6edf3]">Roofline Model — H100 SXM5 BF16</h3>
            <p className="mt-0.5 text-xs text-[#8b949e]">
              Compute ceiling: {PEAK_COMPUTE_TFLOPS} TFLOPS · Memory BW: {PEAK_MEMORY_BW_TB} TB/s · Ridge point: AI ≈{' '}
              {RIDGE_POINT_AI.toFixed(0)} FLOP/Byte
            </p>
          </div>
          {/* Legend */}
          <div className="flex flex-wrap gap-x-4 gap-y-1.5">
            {CATEGORY_ORDER.filter((c) =>
              scatterKernels.some((k) => k.category === c)
            ).map((cat) => (
              <div key={cat} className="flex items-center gap-1.5 text-xs text-[#8b949e]">
                <span
                  style={{
                    display: 'inline-block',
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    backgroundColor: categoryColor(cat),
                  }}
                />
                {cat}
              </div>
            ))}
            <div className="flex items-center gap-1.5 text-xs text-[#8b949e]">
              <span
                style={{
                  display: 'inline-block',
                  width: 16,
                  height: 2,
                  backgroundColor: '#f97583',
                }}
              />
              ceiling
            </div>
          </div>
        </div>

        {allKernels.length === 0 ? (
          <div className="flex h-64 items-center justify-center text-[#8b949e]">
            No data for selected filters
          </div>
        ) : (
          <ChartErrorBoundary>
          <ResponsiveContainer width="100%" height={480}>
            <ComposedChart margin={{ top: 10, right: 24, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
              <XAxis
                dataKey="ai"
                type="number"
                scale="log"
                domain={[0.1, 10000]}
                allowDataOverflow
                tick={{ fill: '#8b949e', fontSize: 11 }}
                axisLine={{ stroke: '#30363d' }}
                tickLine={{ stroke: '#30363d' }}
                tickFormatter={logTick}
                ticks={[0.1, 1, 10, 100, 1000, 10000]}
                label={{
                  value: 'Arithmetic Intensity (FLOP/Byte)',
                  position: 'insideBottom',
                  offset: -28,
                  fill: '#8b949e',
                  fontSize: 12,
                }}
              />
              <YAxis
                dataKey="tflops"
                type="number"
                scale="log"
                domain={[0.01, 2000]}
                allowDataOverflow
                tick={{ fill: '#8b949e', fontSize: 11 }}
                axisLine={{ stroke: '#30363d' }}
                tickLine={{ stroke: '#30363d' }}
                tickFormatter={logTick}
                ticks={[0.01, 0.1, 1, 10, 100, 1000]}
                label={{
                  value: 'Achieved Performance (TFLOPS)',
                  angle: -90,
                  position: 'insideLeft',
                  offset: 10,
                  fill: '#8b949e',
                  fontSize: 12,
                }}
              />
              <Tooltip content={<ScatterTooltip />} />

              {/* Roofline ceiling line */}
              <Line
                data={ROOFLINE_CEILING}
                type="linear"
                dataKey="tflops"
                stroke="#f97583"
                strokeWidth={2}
                dot={false}
                activeDot={false}
                strokeDasharray="6 3"
                legendType="none"
              />

              {/* Ridge point reference */}
              <ReferenceLine
                x={RIDGE_POINT_AI}
                stroke="#f97583"
                strokeDasharray="4 4"
                strokeOpacity={0.4}
                label={{
                  value: `Ridge ~${RIDGE_POINT_AI.toFixed(0)}`,
                  fill: '#f97583',
                  fontSize: 10,
                  position: 'top',
                }}
              />

              {/* Kernel dots — one Scatter per category so each gets its color */}
              {CATEGORY_ORDER.filter((cat) =>
                scatterKernels.some((k) => k.category === cat)
              ).map((cat) => (
                <Scatter
                  key={cat}
                  name={cat}
                  data={scatterKernels.filter((k) => k.category === cat)}
                  shape={<KernelDot />}
                  legendType="none"
                  fill={categoryColor(cat)}
                />
              ))}
            </ComposedChart>
          </ResponsiveContainer>
          </ChartErrorBoundary>
        )}
      </div>

      {/* ── Kernel breakdown (stacked bar) ──────────────────────────────── */}
      <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-[#e6edf3]">Kernel Time Breakdown by Category</h3>
          <p className="mt-0.5 text-xs text-[#8b949e]">% of total CUDA time per batch size</p>
        </div>
        {barData.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-[#8b949e]">
            No data for selected filters
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart
              data={barData}
              margin={{ top: 5, right: 140, bottom: 24, left: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#21262d" vertical={false} />
              <XAxis
                dataKey="batch_size"
                tick={{ fill: '#8b949e', fontSize: 11 }}
                axisLine={{ stroke: '#30363d' }}
                tickLine={false}
                label={{
                  value: 'Batch Size',
                  position: 'insideBottom',
                  offset: -16,
                  fill: '#8b949e',
                  fontSize: 12,
                }}
              />
              <YAxis
                tick={{ fill: '#8b949e', fontSize: 11 }}
                axisLine={{ stroke: '#30363d' }}
                tickLine={false}
                tickFormatter={(v) => `${v}%`}
                domain={[0, 100]}
              />
              <Tooltip content={<BarTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
              <Legend
                layout="vertical"
                align="right"
                verticalAlign="middle"
                wrapperStyle={{ fontSize: 11, color: '#8b949e', paddingLeft: 12 }}
                formatter={(value) => (
                  <span style={{ color: '#8b949e' }}>{value}</span>
                )}
              />
              {presentCategories.map((cat) => (
                <Bar key={cat} dataKey={cat} stackId="a" fill={categoryColor(cat)} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Kernel table (top 20 by CUDA time) ──────────────────────────── */}
      <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-[#e6edf3]">Top Kernels by CUDA Time</h3>
          <p className="mt-0.5 text-xs text-[#8b949e]">Top 20 across all selected batch sizes</p>
        </div>
        {allKernels.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-[#8b949e]">
            No data
          </div>
        ) : (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[700px] text-sm">
              <thead>
                <tr className="border-b border-[#21262d] text-left text-[11px] font-semibold uppercase tracking-widest text-[#8b949e]">
                  <th className="pb-2 pr-4">Kernel</th>
                  <th className="pb-2 pr-4">Category</th>
                  <th className="pb-2 pr-4 text-right">BS</th>
                  <th className="pb-2 pr-4 text-right">CUDA µs</th>
                  <th className="pb-2 pr-4 text-right">AI (FLOP/B)</th>
                  <th className="pb-2 pr-4 text-right">TFLOPS</th>
                  <th className="pb-2 text-right">Bound</th>
                </tr>
              </thead>
              <tbody>
                {[...allKernels]
                  .sort((a, b) => b.cuda_time_us - a.cuda_time_us)
                  .slice(0, 20)
                  .map((k, i) => {
                    const isMem = k.arithmetic_intensity < RIDGE_POINT_AI;
                    return (
                      <tr
                        key={i}
                        className="border-b border-[#21262d]/60 hover:bg-[#21262d]/40 transition-colors"
                      >
                        <td className="py-2 pr-4 text-[#c9d1d9]" style={{ maxWidth: 320 }}>
                          <span
                            className="block truncate font-mono text-xs"
                            title={k.name}
                          >
                            {shortKernelName(k.name)}
                          </span>
                        </td>
                        <td className="py-2 pr-4">
                          <span
                            className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium"
                            style={{
                              backgroundColor: `${categoryColor(k.category)}22`,
                              color: categoryColor(k.category),
                            }}
                          >
                            {k.category}
                          </span>
                        </td>
                        <td className="py-2 pr-4 text-right font-mono text-xs text-[#8b949e]">
                          {k.batch_size}
                        </td>
                        <td className="py-2 pr-4 text-right font-mono text-xs text-[#e6edf3]">
                          {(k.cuda_time_us ?? 0).toFixed(1)}
                        </td>
                        <td className="py-2 pr-4 text-right font-mono text-xs text-[#e6edf3]">
                          {(k.arithmetic_intensity ?? 0).toFixed(1)}
                        </td>
                        <td className="py-2 pr-4 text-right font-mono text-xs text-[#e6edf3]">
                          {(k.achieved_tflops ?? 0).toFixed(2)}
                        </td>
                        <td className="py-2 text-right">
                          <span
                            className="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold"
                            style={{
                              backgroundColor: isMem
                                ? 'rgba(187,187,187,0.12)'
                                : 'rgba(0,114,178,0.15)',
                              color: isMem ? '#BBBBBB' : '#56B4E9',
                            }}
                          >
                            {isMem ? 'mem' : 'compute'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
