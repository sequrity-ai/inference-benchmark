import { useState, useEffect, useMemo, useCallback } from 'react';
import type { BenchmarkResult, FilterState, FilterOptions } from '../types';

export function useData() {
  const [allData, setAllData] = useState<BenchmarkResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    hardware: [],
    model: [],
    backend: [],
    profile: [],
  });

  useEffect(() => {
    fetch(import.meta.env.BASE_URL + 'data.json')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: BenchmarkResult[]) => {
        setAllData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const filterOptions = useMemo<FilterOptions>(() => {
    const hw = new Set<string>();
    const model = new Set<string>();
    const backend = new Set<string>();
    const profile = new Set<string>();

    for (const r of allData) {
      hw.add(r.hardware);
      model.add(r.modelShort);
      backend.add(r.config.backend);
      profile.add(r.config.profile);
    }

    return {
      hardware: Array.from(hw).sort(),
      model: Array.from(model).sort(),
      backend: Array.from(backend).sort(),
      profile: Array.from(profile).sort(),
    };
  }, [allData]);

  const filteredData = useMemo(() => {
    return allData.filter((r) => {
      if (filters.hardware.length > 0 && !filters.hardware.includes(r.hardware)) return false;
      if (filters.model.length > 0 && !filters.model.includes(r.modelShort)) return false;
      if (filters.backend.length > 0 && !filters.backend.includes(r.config.backend)) return false;
      if (filters.profile.length > 0 && !filters.profile.includes(r.config.profile)) return false;
      return true;
    });
  }, [allData, filters]);

  // Group data by series key for chart rendering
  const seriesData = useMemo(() => {
    const map = new Map<string, BenchmarkResult[]>();
    for (const r of filteredData) {
      const existing = map.get(r.seriesKey) || [];
      existing.push(r);
      map.set(r.seriesKey, existing);
    }
    // Sort each series by concurrency
    for (const [, arr] of map) {
      arr.sort((a, b) => a.config.concurrency - b.config.concurrency);
    }
    return map;
  }, [filteredData]);

  const toggleFilter = useCallback((category: keyof FilterState, value: string) => {
    setFilters((prev) => {
      const arr = prev[category];
      const next = arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
      return { ...prev, [category]: next };
    });
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({ hardware: [], model: [], backend: [], profile: [] });
  }, []);

  return {
    allData,
    data: filteredData,
    seriesData,
    loading,
    error,
    filters,
    filterOptions,
    toggleFilter,
    clearFilters,
  };
}
