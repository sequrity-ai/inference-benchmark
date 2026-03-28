"""
Parse profiler output (PyTorch Profiler JSON or ncu CSV) into structured
data for roofline plotting.

For PyTorch profiler output: extracts per-kernel timing and FLOPs.
Computes theoretical arithmetic intensity for GEMM kernels from known
model architecture parameters.
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.roofline.roofline_config import classify_kernel, H100_SXM


@dataclass
class KernelRecord:
    name: str
    category: str
    cuda_time_us: float
    calls: int
    flops: float
    # For roofline: theoretical estimates
    theoretical_bytes: float      # estimated DRAM bytes from tensor shapes
    arithmetic_intensity: float   # FLOPs / byte
    achieved_tflops: float


def estimate_gemm_bytes(input_shapes_str: str) -> float:
    """Estimate DRAM bytes for a GEMM from input shapes.

    For aten::mm with inputs [M,K] and [K,N]:
    - Read A: M*K elements
    - Read B: K*N elements
    - Write C: M*N elements
    All in BF16 (2 bytes per element).
    """
    # Parse shapes like "[[4, 512, 4096], [4096, 14336]]" or "[[4, 512, 4096], [14336, 4096]]"
    try:
        # Find all dimension lists
        dims = re.findall(r'\[[\d,\s]+\]', input_shapes_str)
        if len(dims) < 2:
            return 0

        def parse_dims(s):
            return [int(x.strip()) for x in s.strip('[]').split(',')]

        a_dims = parse_dims(dims[0])
        b_dims = parse_dims(dims[1])

        # Flatten batch dims: last 2 dims are the matrix dims
        if len(a_dims) >= 2:
            M = 1
            for d in a_dims[:-1]:
                M *= d
            K_a = a_dims[-1]
        else:
            return 0

        if len(b_dims) >= 2:
            K_b = b_dims[-2] if len(b_dims) == 2 else b_dims[-2]
            N = b_dims[-1]
        else:
            return 0

        # BF16: 2 bytes per element
        bytes_a = M * K_a * 2
        bytes_b = K_b * N * 2
        bytes_c = M * N * 2
        return bytes_a + bytes_b + bytes_c

    except Exception:
        return 0


def parse_torch_profiler_json(data: dict) -> list[KernelRecord]:
    """Parse a PyTorch profiler JSON output into KernelRecords."""
    records = []

    for k in data.get("kernel_summary", []):
        name = k["name"]
        category = classify_kernel(name)
        cuda_time_us = k["cuda_time_us"]
        calls = k["calls"]
        flops = k["flops"]

        # Estimate bytes for GEMM operations
        theoretical_bytes = 0
        if category == "gemm" or "mm" in name.lower():
            theoretical_bytes = estimate_gemm_bytes(k.get("input_shapes", ""))
            if theoretical_bytes == 0 and flops > 0:
                # Fallback: for BF16 GEMM, AI ≈ M*N*K*2 / (M*K + K*N + M*N) * 2bytes
                # Typical AI for large GEMMs is ~100-300 FLOP/byte
                # Use a conservative estimate based on known H100 characteristics
                theoretical_bytes = flops / 200  # assume ~200 FLOP/byte for large GEMM

        elif flops == 0 and cuda_time_us > 0:
            # Memory-bound kernel: estimate bytes from duration assuming peak bandwidth
            # peak_bw = 3.35 TB/s = 3.35e12 bytes/s = 3.35e6 bytes/us
            theoretical_bytes = cuda_time_us * H100_SXM.hbm_bandwidth_tb_s * 1e6

            # Estimate FLOPs for elementwise ops: ~1-2 FLOPs per element
            # For typical BF16 elementwise: read + write = 4 bytes, 1-2 FLOPs
            if category in ("elementwise", "activation", "reduce", "layernorm", "rope"):
                flops = theoretical_bytes * 0.5  # ~0.5 FLOP/byte for elementwise
            elif category == "attention":
                # Flash attention FLOPs: 2 * batch * heads * seq_len^2 * head_dim
                # We don't know exact dims, so estimate from time relative to GEMM
                flops = theoretical_bytes * 50  # attention is moderately compute-heavy
            elif category == "memory":
                flops = 0  # pure data movement
                theoretical_bytes = cuda_time_us * H100_SXM.hbm_bandwidth_tb_s * 1e6

        # Compute derived metrics
        if theoretical_bytes > 0 and flops > 0:
            arithmetic_intensity = flops / theoretical_bytes
        elif category == "memory":
            arithmetic_intensity = 0.01  # pure memory ops
        else:
            arithmetic_intensity = 0

        if cuda_time_us > 0 and flops > 0:
            achieved_tflops = flops / (cuda_time_us * 1e-6) / 1e12
        elif cuda_time_us > 0 and theoretical_bytes > 0:
            # For memory-bound kernels, report achieved bandwidth as TFLOPS equivalent
            achieved_bw_tb_s = theoretical_bytes / (cuda_time_us * 1e-6) / 1e12
            achieved_tflops = achieved_bw_tb_s * arithmetic_intensity
        else:
            achieved_tflops = 0

        records.append(KernelRecord(
            name=name,
            category=category,
            cuda_time_us=cuda_time_us,
            calls=calls,
            flops=flops,
            theoretical_bytes=theoretical_bytes,
            arithmetic_intensity=arithmetic_intensity,
            achieved_tflops=achieved_tflops,
        ))

    return records


def summarize_by_category(records: list[KernelRecord]) -> dict:
    """Aggregate kernel records by category."""
    cats: dict[str, dict] = {}
    total_time = sum(r.cuda_time_us for r in records)

    for r in records:
        if r.category not in cats:
            cats[r.category] = {
                "total_cuda_time_us": 0,
                "total_flops": 0,
                "total_bytes": 0,
                "kernel_count": 0,
                "call_count": 0,
                "duration_pct": 0,
            }
        c = cats[r.category]
        c["total_cuda_time_us"] += r.cuda_time_us
        c["total_flops"] += r.flops
        c["total_bytes"] += r.theoretical_bytes
        c["kernel_count"] += 1
        c["call_count"] += r.calls

    for cat, c in cats.items():
        c["duration_pct"] = (c["total_cuda_time_us"] / total_time * 100) if total_time > 0 else 0
        if c["total_bytes"] > 0:
            c["avg_arithmetic_intensity"] = c["total_flops"] / c["total_bytes"]
        else:
            c["avg_arithmetic_intensity"] = 0
        if c["total_cuda_time_us"] > 0:
            c["avg_achieved_tflops"] = c["total_flops"] / (c["total_cuda_time_us"] * 1e-6) / 1e12
        else:
            c["avg_achieved_tflops"] = 0

    return cats


def parse_file(input_path: Path) -> dict:
    """Parse a profiler output JSON file."""
    data = json.loads(input_path.read_text())

    records = parse_torch_profiler_json(data)
    summary = summarize_by_category(records)

    return {
        "model": data.get("model", "unknown"),
        "phase": data.get("phase", "unknown"),
        "batch_size": data.get("batch_size", 0),
        "seq_len": data.get("seq_len", 0),
        "num_layers_profiled": data.get("num_layers_profiled", 0),
        "profiler": data.get("profiler", "torch"),
        "source_file": input_path.name,
        "total_kernels": len(records),
        "kernels": [asdict(r) for r in records],
        "category_summary": summary,
    }


def main():
    parser = argparse.ArgumentParser(description="Parse profiler output for roofline analysis")
    parser.add_argument("--input", type=str, required=True,
                        help="Input JSON file or glob pattern")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: results/roofline/parsed/)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    output_dir = Path(args.output_dir) if args.output_dir else project_root / "results" / "roofline" / "parsed"
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = Path(args.input)
    if "*" in args.input:
        files = sorted(input_path.parent.glob(input_path.name))
    else:
        files = [input_path]

    for f in files:
        if not f.exists() or not f.suffix == ".json":
            continue

        print(f"Parsing: {f.name}...")
        try:
            result = parse_file(f)
            out_path = output_dir / f.name
            out_path.write_text(json.dumps(result, indent=2))

            # Print summary
            print(f"  {result['total_kernels']} kernels")
            for cat, info in sorted(result["category_summary"].items(), key=lambda x: -x[1]["duration_pct"]):
                print(f"    {cat:20s}: {info['duration_pct']:5.1f}% | "
                      f"AI={info['avg_arithmetic_intensity']:.1f} FLOP/B | "
                      f"{info['avg_achieved_tflops']:.2f} TFLOPS")
            print(f"  Output: {out_path}")
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nDone. Parsed {len(files)} file(s).")


if __name__ == "__main__":
    main()
