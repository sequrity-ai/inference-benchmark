import { useState } from 'react';
import { useData } from './hooks/useData';
import { Layout } from './components/Layout';
import { KPICards } from './components/KPICards';
import { Filters } from './components/Filters';
import { Tabs } from './components/Tabs';
import { LatencyChart } from './components/charts/LatencyChart';
import { ThroughputChart } from './components/charts/ThroughputChart';
import { ComparisonChart } from './components/charts/ComparisonChart';
import { DataTable } from './components/DataTable';
import type { TabId } from './types';
import './index.css';

function App() {
  const {
    allData,
    data,
    seriesData,
    loading,
    error,
    filters,
    filterOptions,
    toggleFilter,
    clearFilters,
  } = useData();

  const [activeTab, setActiveTab] = useState<TabId>('latency');

  if (error) {
    return (
      <Layout totalRuns={0} loading={false}>
        <div className="flex h-64 items-center justify-center rounded-lg border border-[#f97583]/30 bg-[#f97583]/10 text-[#f97583]">
          <div className="text-center">
            <div className="mb-2 text-lg font-semibold">Failed to load data</div>
            <div className="text-sm">{error}</div>
            <div className="mt-2 text-xs text-[#8b949e]">
              Run <code className="rounded bg-[#21262d] px-1">npx tsx scripts/build-data.ts</code> to generate data.json
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout totalRuns={allData.length} loading={loading}>
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="text-[#8b949e]">Loading benchmark data...</div>
        </div>
      ) : (
        <>
          <KPICards data={data} allData={allData} />
          <Filters
            filters={filters}
            options={filterOptions}
            onToggle={toggleFilter}
            onClear={clearFilters}
          />
          <Tabs active={activeTab} onChange={setActiveTab} />

          {activeTab === 'latency' && <LatencyChart seriesData={seriesData} />}
          {activeTab === 'throughput' && <ThroughputChart seriesData={seriesData} />}
          {activeTab === 'comparison' && <ComparisonChart seriesData={seriesData} />}
          {activeTab === 'raw' && <DataTable data={data} />}
        </>
      )}
    </Layout>
  );
}

export default App;
