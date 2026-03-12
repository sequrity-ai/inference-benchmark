"""
Benchmark runner — orchestrates a full benchmark run.

Usage:
    python -m src.benchmark.runner \
        --url http://localhost:8000/v1/chat/completions \
        --model meta-llama/Llama-3.1-8B-Instruct \
        --backend vllm \
        --profile output-short \
        --concurrency 10 \
        --num-requests 100 \
        --api-key test \
        --output results/run_001.json

    # TRT-LLM (point URL at /generate_stream):
    python -m src.benchmark.runner \
        --url http://localhost:8000/generate_stream \
        --model meta-llama/Llama-3.1-8B-Instruct \
        --backend trtllm \
        --profile output-short \
        --concurrency 10 \
        --num-requests 100
"""

import asyncio
import argparse
import json
import time
import os
from pathlib import Path

import aiohttp

from .metrics import aggregate, print_summary
from ..workloads.profiles import get_profile
from ..workloads.dataset import make_dataset
from ..workloads.arrival import make_arrival_times
from ..engines import get_backend, SUPPORTED_BACKENDS


async def run_benchmark(
    url: str,
    model: str,
    profile_name: str,
    concurrency: int,
    num_requests: int,
    backend_name: str = "vllm",
    api_key: str = "test",
    arrival_pattern: str = "steady",
    target_rate: float = 10.0,
    warmup_requests: int = 3,
    seed: int = 42,
    timeout: int = 120,
    ignore_eos: bool = False,
):
    """
    Run a benchmark and return (results, duration).
    """
    backend = get_backend(backend_name)
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
            await backend.run_warmup(url, model, api_key, warmup_requests, timeout)
            print("Warmup done.")

        # Schedule requests
        semaphore = asyncio.Semaphore(concurrency)
        results = [None] * num_requests
        benchmark_start = time.perf_counter()

        async def dispatch(i: int, dispatch_time: float):
            now = time.perf_counter() - benchmark_start
            delay = dispatch_time - now
            if delay > 0:
                await asyncio.sleep(delay)

            request = dataset.get_next_request()
            async with semaphore:
                result = await backend.send_request(
                    session=session,
                    url=url,
                    model=model,
                    messages=request.messages,
                    max_tokens=request.max_tokens,
                    api_key=api_key,
                    ignore_eos=ignore_eos,
                )
            results[i] = result

        tasks = [dispatch(i, t) for i, t in enumerate(arrival_times)]
        await asyncio.gather(*tasks)

    benchmark_duration = time.perf_counter() - benchmark_start
    return results, benchmark_duration


def save_results(summary, results, output_path: str, config: dict):
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
    parser.add_argument("--url", required=True, help="Server endpoint URL")
    parser.add_argument("--model", required=True)
    parser.add_argument("--backend", default="vllm", choices=SUPPORTED_BACKENDS,
                        help="Backend type (vllm/sglang/openai → /v1/chat/completions, trtllm → /generate_stream)")
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
    parser.add_argument("--ignore-eos", action="store_true",
                        help="Pass ignore_eos=true to vLLM (needed for FP8 models with random token workloads)")
    parser.add_argument("--mode", choices=["stress-test", "single-turn", "multi-turn"],
                        help="Benchmark mode (sets profile defaults and required flags). "
                             "Use --profile for a specific profile within a mode.")
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()

    if args.mode:
        if args.mode == "multi-turn":
            print("ERROR: multi-turn mode not yet implemented. See src/modes/multi_turn.py.")
            import sys; sys.exit(1)
        if args.mode == "stress-test":
            if not args.ignore_eos:
                print("NOTE: stress-test mode auto-enables --ignore-eos (required for FP8 models)")
                args.ignore_eos = True
            if args.profile == "output-short":  # default — override for stress-test
                args.profile = "random-inferencex"
        if args.mode == "single-turn":
            print("NOTE: single-turn mode requires server launched with --enable-prefix-caching (vLLM)")
            print("      or radix cache (SGLang default). See scripts/launch_server.sh")

    config = {**vars(args), "mode": args.mode}

    results, duration = asyncio.run(run_benchmark(
        url=args.url,
        model=args.model,
        profile_name=args.profile,
        concurrency=args.concurrency,
        num_requests=args.num_requests,
        backend_name=args.backend,
        api_key=args.api_key,
        arrival_pattern=args.arrival,
        target_rate=args.target_rate,
        warmup_requests=args.warmup,
        seed=args.seed,
        timeout=args.timeout,
        ignore_eos=args.ignore_eos,
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
