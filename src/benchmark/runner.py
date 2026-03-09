"""
Benchmark runner — orchestrates a full benchmark run.

Usage:
    python -m src.benchmark.runner \
        --url http://localhost:8000/v1/chat/completions \
        --model meta-llama/Llama-3.1-8B-Instruct \
        --profile output-short \
        --concurrency 10 \
        --num-requests 100 \
        --api-key test \
        --output results/run_001.json
"""

import asyncio
import argparse
import json
import time
import os
from pathlib import Path

import aiohttp

from .client import send_chat_request, run_warmup, RequestResult
from .metrics import aggregate, print_summary
from ..workloads.profiles import get_profile
from ..workloads.dataset import make_dataset
from ..workloads.arrival import make_arrival_times


async def run_benchmark(
    url: str,
    model: str,
    profile_name: str,
    concurrency: int,
    num_requests: int,
    api_key: str = "test",
    arrival_pattern: str = "steady",
    target_rate: float = 10.0,
    warmup_requests: int = 3,
    seed: int = 42,
    timeout: int = 120,
) -> list[RequestResult]:
    """
    Run a benchmark and return per-request results.
    """
    profile = get_profile(profile_name)
    dataset = make_dataset(profile)
    arrival_times = make_arrival_times(
        pattern=arrival_pattern,
        num_requests=num_requests,
        concurrency=concurrency,
        target_rate=target_rate,
        seed=seed,
    )

    connector = aiohttp.TCPConnector(limit=concurrency + 10)
    client_timeout = aiohttp.ClientTimeout(total=timeout)

    async with aiohttp.ClientSession(connector=connector, timeout=client_timeout) as session:
        # Warmup
        if warmup_requests > 0:
            print(f"Warming up with {warmup_requests} requests...")
            await run_warmup(url, model, api_key, warmup_requests, timeout)
            print("Warmup done.")

        # Schedule requests according to arrival pattern
        semaphore = asyncio.Semaphore(concurrency)
        results: list[RequestResult] = [None] * num_requests
        benchmark_start = time.perf_counter()

        async def dispatch(i: int, dispatch_time: float):
            # Wait until scheduled dispatch time
            now = time.perf_counter() - benchmark_start
            delay = dispatch_time - now
            if delay > 0:
                await asyncio.sleep(delay)

            messages = dataset.get_next_messages()
            async with semaphore:
                result = await send_chat_request(
                    session=session,
                    url=url,
                    model=model,
                    messages=messages,
                    max_tokens=profile.osl_tokens,
                    api_key=api_key,
                )
            results[i] = result

        tasks = [dispatch(i, t) for i, t in enumerate(arrival_times)]
        await asyncio.gather(*tasks)

    benchmark_duration = time.perf_counter() - benchmark_start
    return results, benchmark_duration


def save_results(summary, results: list[RequestResult], output_path: str, config: dict):
    """Save summary + per-request data to JSON."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    output = {
        "config": config,
        "summary": summary.to_dict(),
        "per_request": [
            {
                "success": r.success,
                "ttft_ms": round(r.ttft * 1000, 2) if r.ttft else None,
                "tpot_ms": round(r.tpot * 1000, 2) if r.tpot else None,
                "e2el_ms": round(r.e2el * 1000, 2) if r.e2el else None,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "error": r.error,
            }
            for r in results if r is not None
        ],
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to: {output_path}")


def get_args():
    parser = argparse.ArgumentParser(description="inference-benchmark runner")
    parser.add_argument("--url", required=True, help="OpenAI-compatible chat completions URL")
    parser.add_argument("--model", required=True)
    parser.add_argument("--profile", default="output-short", help="Workload profile name")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--num-requests", type=int, default=100)
    parser.add_argument("--api-key", default="test")
    parser.add_argument("--arrival", default="steady", choices=["steady", "poisson", "ramp"])
    parser.add_argument("--target-rate", type=float, default=10.0, help="req/s for poisson/ramp")
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", default="results/latest.json")
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()

    config = vars(args)

    results, duration = asyncio.run(run_benchmark(
        url=args.url,
        model=args.model,
        profile_name=args.profile,
        concurrency=args.concurrency,
        num_requests=args.num_requests,
        api_key=args.api_key,
        arrival_pattern=args.arrival,
        target_rate=args.target_rate,
        warmup_requests=args.warmup,
        seed=args.seed,
        timeout=args.timeout,
    ))

    summary = aggregate(
        results=[r for r in results if r is not None],
        duration_s=duration,
        model=args.model,
        profile=args.profile,
        concurrency=args.concurrency,
    )

    print_summary(summary)
    save_results(summary, results, args.output, config)
