"""
Metrics aggregation for benchmark results.

Computes p50/p90/p99 for TTFT, TPOT, ITL, E2EL.
Tracks successful vs failed requests separately.
Reports input tok/s and output tok/s separately (not just total).
"""

from dataclasses import dataclass, field
from typing import Optional
import statistics
import json
import time


@dataclass
class BenchmarkSummary:
    """Aggregated metrics for a benchmark run."""

    # Run config
    model: str = ""
    profile: str = ""
    concurrency: int = 0
    num_requests: int = 0
    duration_s: float = 0.0

    # Request counts
    successful_requests: int = 0
    failed_requests: int = 0

    # Throughput
    request_throughput: float = 0.0     # req/s
    input_token_throughput: float = 0.0  # input tok/s
    output_token_throughput: float = 0.0  # output tok/s
    total_token_throughput: float = 0.0   # (input + output) tok/s

    # Token counts
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    # TTFT (ms)
    mean_ttft_ms: float = 0.0
    median_ttft_ms: float = 0.0
    p90_ttft_ms: float = 0.0
    p99_ttft_ms: float = 0.0

    # TPOT / mean ITL (ms) — time per output token excluding first
    mean_tpot_ms: float = 0.0
    median_tpot_ms: float = 0.0
    p90_tpot_ms: float = 0.0
    p99_tpot_ms: float = 0.0

    # E2EL (ms)
    mean_e2el_ms: float = 0.0
    median_e2el_ms: float = 0.0
    p90_e2el_ms: float = 0.0
    p99_e2el_ms: float = 0.0

    # Errors
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "errors"}
        d["errors"] = self.errors[:10]  # cap error list in JSON
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _percentile(data: list[float], p: float) -> float:
    """Compute p-th percentile (0-100) of a sorted or unsorted list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (p / 100) * (len(sorted_data) - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sorted_data):
        return sorted_data[-1]
    frac = idx - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


def aggregate(results, duration_s: float, model: str = "", profile: str = "", concurrency: int = 0) -> BenchmarkSummary:
    """
    Aggregate a list of RequestResult into a BenchmarkSummary.

    Args:
        results: list of RequestResult from client.py
        duration_s: total wall-clock time for the benchmark run
        model: model name for labeling
        profile: workload profile name for labeling
        concurrency: concurrency level used
    """
    summary = BenchmarkSummary(
        model=model,
        profile=profile,
        concurrency=concurrency,
        num_requests=len(results),
        duration_s=duration_s,
    )

    ttfts = []
    tpots = []
    e2els = []

    for r in results:
        if r.success:
            summary.successful_requests += 1
            summary.total_input_tokens += r.input_tokens
            summary.total_output_tokens += r.output_tokens

            if r.ttft is not None:
                ttfts.append(r.ttft * 1000)  # convert to ms
            if r.tpot is not None:
                tpots.append(r.tpot * 1000)
            if r.e2el is not None:
                e2els.append(r.e2el * 1000)
        else:
            summary.failed_requests += 1
            if r.error:
                summary.errors.append(r.error)

    if duration_s > 0:
        summary.request_throughput = summary.successful_requests / duration_s
        summary.input_token_throughput = summary.total_input_tokens / duration_s
        summary.output_token_throughput = summary.total_output_tokens / duration_s
        summary.total_token_throughput = (
            summary.total_input_tokens + summary.total_output_tokens
        ) / duration_s

    if ttfts:
        summary.mean_ttft_ms = statistics.mean(ttfts)
        summary.median_ttft_ms = statistics.median(ttfts)
        summary.p90_ttft_ms = _percentile(ttfts, 90)
        summary.p99_ttft_ms = _percentile(ttfts, 99)

    if tpots:
        summary.mean_tpot_ms = statistics.mean(tpots)
        summary.median_tpot_ms = statistics.median(tpots)
        summary.p90_tpot_ms = _percentile(tpots, 90)
        summary.p99_tpot_ms = _percentile(tpots, 99)

    if e2els:
        summary.mean_e2el_ms = statistics.mean(e2els)
        summary.median_e2el_ms = statistics.median(e2els)
        summary.p90_e2el_ms = _percentile(e2els, 90)
        summary.p99_e2el_ms = _percentile(e2els, 99)

    return summary


def print_summary(s: BenchmarkSummary) -> None:
    """Print a formatted benchmark summary to stdout."""
    print(f"\n{'=' * 52}")
    print(f" Benchmark Results: {s.profile} | concurrency={s.concurrency}")
    print(f"{'=' * 52}")
    print(f" Model:                    {s.model}")
    print(f" Duration:                 {s.duration_s:.2f}s")
    print(f" Requests:                 {s.successful_requests} ok / {s.failed_requests} failed")
    print(f" Request throughput:       {s.request_throughput:.2f} req/s")
    print(f" Input token throughput:   {s.input_token_throughput:.0f} tok/s")
    print(f" Output token throughput:  {s.output_token_throughput:.0f} tok/s")
    print(f" Total token throughput:   {s.total_token_throughput:.0f} tok/s")
    print(f"{'─' * 52}")
    print(f" TTFT  mean/p50/p90/p99:   {s.mean_ttft_ms:.1f} / {s.median_ttft_ms:.1f} / {s.p90_ttft_ms:.1f} / {s.p99_ttft_ms:.1f} ms")
    print(f" TPOT  mean/p50/p90/p99:   {s.mean_tpot_ms:.1f} / {s.median_tpot_ms:.1f} / {s.p90_tpot_ms:.1f} / {s.p99_tpot_ms:.1f} ms")
    print(f" E2EL  mean/p50/p90/p99:   {s.mean_e2el_ms:.1f} / {s.median_e2el_ms:.1f} / {s.p90_e2el_ms:.1f} / {s.p99_e2el_ms:.1f} ms")
    print(f"{'=' * 52}\n")
    if s.errors:
        print(f" Errors ({len(s.errors)} total, first {min(3,len(s.errors))}):")
        for e in s.errors[:3]:
            print(f"   {e}")
        print()
