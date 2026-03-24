import type { ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
  totalRuns: number;
  loading: boolean;
}

export function Layout({ children, totalRuns, loading }: LayoutProps) {
  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      {/* Sticky nav */}
      <nav className="sticky top-0 z-50 border-b border-[#21262d] bg-[#161b22]/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#00bcd4]/15 text-[#00bcd4]" style={{ boxShadow: '0 0 0 1px rgba(0,188,212,0.2), 0 0 8px rgba(0,188,212,0.12)' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
            <h1 className="text-base font-semibold tracking-tight sm:text-lg">
              Inference Benchmark
            </h1>
          </div>
          <div className="flex items-center gap-4 text-sm text-[#8b949e]">
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[#ff9800]" />
                Loading...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <span className="inline-block h-2 w-2 rounded-full bg-[#3fb950]" />
                <span className="font-mono">{totalRuns}</span> runs loaded
              </span>
            )}
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        {children}
      </main>
    </div>
  );
}
