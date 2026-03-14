"""Load benchmark result JSON files into a pandas DataFrame."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

import pandas as pd

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "results"

# ---------------------------------------------------------------------------
# Hardware detection heuristics
# ---------------------------------------------------------------------------

_HW_PATTERNS = [
    (re.compile(r"h100x2", re.I), "H100x2"),
    (re.compile(r"h100", re.I), "H100"),
    (re.compile(r"a6000", re.I), "A6000"),
    (re.compile(r"a100", re.I), "A100"),
    (re.compile(r"l40", re.I), "L40S"),
]


def _detect_hardware(filepath: Path, config: dict) -> str:
    """Infer hardware tag from filepath components and config fields."""
    # Check directory name first (e.g. h100_70b_fp8/)
    parts = filepath.relative_to(RESULTS_DIR).parts if filepath.is_relative_to(RESULTS_DIR) else filepath.parts
    search_str = "/".join(parts)

    # Also check the output field in config
    output_field = config.get("output", "")
    search_str = f"{search_str} {output_field}"

    for pat, label in _HW_PATTERNS:
        if pat.search(search_str):
            return label

    # Check URL for known cloud patterns
    url = config.get("url", "")
    if "runpod" in url.lower():
        return "RunPod"

    return "unknown"


def _detect_model_short(model_full: str) -> str:
    """Shorten model name for display: 'neuralmagic/Meta-Llama-3.1-70B-Instruct-FP8' -> 'Llama-3.1-70B-FP8'."""
    name = model_full.split("/")[-1]  # strip org prefix
    # Common simplifications
    name = re.sub(r"Meta-", "", name)
    name = re.sub(r"-Instruct", "", name)
    # Collapse redundant parts
    name = re.sub(r"meta-llama--", "", name, flags=re.I)
    return name


def _detect_quant(filepath: Path, config: dict) -> str:
    """Detect quantization from filename or model name."""
    search = f"{filepath.name} {config.get('model', '')}"
    if re.search(r"fp8", search, re.I):
        return "FP8"
    if re.search(r"bf16|bfloat16", search, re.I):
        return "BF16"
    if re.search(r"fp16|float16", search, re.I):
        return "FP16"
    if re.search(r"int8|w8a8", search, re.I):
        return "INT8"
    if re.search(r"int4|awq|gptq", search, re.I):
        return "INT4"
    return "unknown"


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

def load_single(filepath: Path) -> Optional[dict]:
    """Load a single benchmark JSON and return a flat dict or None on failure."""
    try:
        with open(filepath) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    config = data.get("config", {})
    summary = data.get("summary", {})

    if not summary:
        return None

    # Must have at least concurrency and some metric to be useful
    concurrency = summary.get("concurrency") or config.get("concurrency")
    if concurrency is None:
        return None

    hardware = _detect_hardware(filepath, config)
    model_full = summary.get("model") or config.get("model", "unknown")
    model_short = _detect_model_short(model_full)
    quant = _detect_quant(filepath, config)
    backend = config.get("backend", "unknown")
    # Override backend from filename if it starts with a known engine name
    fname_lower = filepath.stem.lower()
    if fname_lower.startswith("sglang"):
        backend = "sglang"
    elif fname_lower.startswith("trtllm") or fname_lower.startswith("trt_llm"):
        backend = "trtllm"
    profile = summary.get("profile") or config.get("profile", "unknown")
    arrival = config.get("arrival", "steady")
    ignore_eos = config.get("ignore_eos", False)
    mode = config.get("mode")

    # Build series key for grouping line charts
    series = f"{hardware} / {model_short} / {backend} / {profile}"

    row = {
        "file": str(filepath),
        "filename": filepath.name,
        "hardware": hardware,
        "model": model_full,
        "model_short": model_short,
        "quant": quant,
        "backend": backend,
        "profile": profile,
        "arrival": arrival,
        "ignore_eos": ignore_eos,
        "mode": mode or "",
        "concurrency": int(concurrency),
        "num_requests": summary.get("num_requests") or config.get("num_requests", 0),
        "series": series,
        # Duration / counts
        "duration_s": summary.get("duration_s", 0),
        "successful_requests": summary.get("successful_requests", 0),
        "failed_requests": summary.get("failed_requests", 0),
        # Throughput
        "request_throughput": summary.get("request_throughput", 0),
        "input_tok_s": summary.get("input_token_throughput", 0),
        "output_tok_s": summary.get("output_token_throughput", 0),
        "total_tok_s": summary.get("total_token_throughput", 0),
        "total_input_tokens": summary.get("total_input_tokens", 0),
        "total_output_tokens": summary.get("total_output_tokens", 0),
        # TTFT
        "mean_ttft_ms": summary.get("mean_ttft_ms"),
        "median_ttft_ms": summary.get("median_ttft_ms"),
        "p90_ttft_ms": summary.get("p90_ttft_ms"),
        "p99_ttft_ms": summary.get("p99_ttft_ms"),
        # TPOT
        "mean_tpot_ms": summary.get("mean_tpot_ms"),
        "median_tpot_ms": summary.get("median_tpot_ms"),
        "p90_tpot_ms": summary.get("p90_tpot_ms"),
        "p99_tpot_ms": summary.get("p99_tpot_ms"),
        # E2EL
        "mean_e2el_ms": summary.get("mean_e2el_ms"),
        "median_e2el_ms": summary.get("median_e2el_ms"),
        "p90_e2el_ms": summary.get("p90_e2el_ms"),
        "p99_e2el_ms": summary.get("p99_e2el_ms"),
        # Error info
        "error_count": len(summary.get("errors", [])),
    }
    return row


def load_per_request(filepath: Path) -> Optional[pd.DataFrame]:
    """Load per-request data from a single result file."""
    try:
        with open(filepath) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    per_req = data.get("per_request", [])
    if not per_req:
        return None

    df = pd.DataFrame(per_req)
    df["file"] = str(filepath)
    df["filename"] = filepath.name
    return df


def load_all(results_dir: Optional[Path] = None) -> pd.DataFrame:
    """Recursively load all benchmark JSONs and return a summary DataFrame."""
    root = results_dir or RESULTS_DIR
    rows = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            if not fname.endswith(".json"):
                continue
            fp = Path(dirpath) / fname
            row = load_single(fp)
            if row is not None:
                rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Sort for consistent display
    df.sort_values(["hardware", "model_short", "backend", "profile", "concurrency"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def get_filter_options(df: pd.DataFrame) -> dict:
    """Return unique values for each filterable column."""
    cols = ["hardware", "model_short", "backend", "profile", "quant", "arrival", "mode"]
    return {c: sorted(df[c].dropna().unique().tolist()) for c in cols if c in df.columns}


def get_series_list(df: pd.DataFrame) -> list[str]:
    """Return unique series identifiers."""
    if "series" not in df.columns:
        return []
    return sorted(df["series"].unique().tolist())
