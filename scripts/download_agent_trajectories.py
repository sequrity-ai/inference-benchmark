#!/usr/bin/env python3
"""
Download and extract multi-turn agent trajectories from GCS.

Reads trajectory.json files from harbor/jobs/ runs, extracts per-turn
messages with growing conversation history, and saves as JSONL files
suitable for TrajectoryMultiTurnDataset.

Output format (one JSON per line):
{
    "session_id": "astropy__astropy-14508",
    "source": "swebench",
    "run": "codex-gpt5.2-swebench-verified-2026-02-16-1700",
    "num_turns": 15,
    "turns": [
        {
            "turn_idx": 0,
            "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
            "osl_tokens": 200
        },
        {
            "turn_idx": 1,
            "messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}, {"role": "user", ...}],
            "osl_tokens": 150
        },
        ...
    ]
}

Usage:
    python scripts/download_agent_trajectories.py [--source swebench|terminalbench|all]
"""

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.expanduser("~/gcp-key.json")

try:
    from google.cloud import storage
except ImportError:
    print("Installing google-cloud-storage...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "google-cloud-storage", "-q"], check=True)
    from google.cloud import storage

BUCKET_NAME = "sequrity-experiments"

# Map source type to GCS run prefixes
RUN_PREFIXES = {
    "swebench": [
        "harbor/jobs/codex-gpt5.2-swebench-verified-2026-02-16-1700/",
        "harbor/jobs/codex-gpt5.2-swebench-verified-2026-02-16-1800/",
    ],
    "terminalbench": [
        "harbor/jobs/codex-gpt5.2-terminal-bench-2026-02-16-2300/",
        "harbor/jobs/codex-gpt5.2-terminal-bench-2026-02-17-0955/",
        "harbor/jobs/codex-gpt5.2-terminal-bench-2026-02-17-1446/",
    ],
}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"


def estimate_tokens(text: str) -> int:
    """Rough token estimate: words * 1.35."""
    return max(1, int(len(text.split()) * 1.35))


def extract_turns_from_trajectory(trajectory: dict) -> list[dict]:
    """
    Extract multi-turn conversation from ATIF-v1.5 trajectory.

    Builds growing message history from steps:
    - source=system → system message
    - source=user → user message
    - source=agent → assistant message (may include tool calls)

    Returns list of turn dicts with growing messages + osl estimate.
    """
    steps = trajectory.get("steps", [])
    if not steps:
        return []

    # Build the full conversation as a flat message list
    messages: list[dict] = []
    turns: list[dict] = []

    for step in steps:
        source = step.get("source", "")
        content = step.get("message", "")

        if not content:
            continue

        if source == "system":
            messages.append({"role": "system", "content": content})
        elif source == "user":
            messages.append({"role": "user", "content": content})
            # Each user message after the first is a new "turn" boundary
            # (tool results come back as user messages in ATIF format)
        elif source == "agent":
            # Agent response — this completes a turn
            osl_est = estimate_tokens(content)
            turns.append({
                "turn_idx": len(turns),
                "messages": list(messages),  # snapshot of context so far
                "osl_tokens": osl_est,
            })
            messages.append({"role": "assistant", "content": content})

    return turns


def list_task_prefixes(client: storage.Client, run_prefix: str) -> list[str]:
    """List all task directories under a run prefix."""
    bucket = client.bucket(BUCKET_NAME)
    it = bucket.list_blobs(prefix=run_prefix, delimiter="/")
    list(it)  # consume iterator
    # Filter out config.json and non-task prefixes
    return [p for p in sorted(it.prefixes) if not p.endswith("config.json")]


def download_trajectory(client: storage.Client, task_prefix: str) -> dict | None:
    """Download trajectory.json for a task."""
    bucket = client.bucket(BUCKET_NAME)
    blob_path = task_prefix + "agent/trajectory.json"
    blob = bucket.blob(blob_path)
    try:
        return json.loads(blob.download_as_text())
    except Exception as e:
        print(f"  WARN: Could not download {blob_path}: {e}")
        return None


def process_run(client: storage.Client, run_prefix: str, source: str) -> list[dict]:
    """Process all tasks in a run, return list of session dicts."""
    run_name = run_prefix.rstrip("/").split("/")[-1]
    print(f"\n--- Run: {run_name} ---")

    task_prefixes = list_task_prefixes(client, run_prefix)
    print(f"  Found {len(task_prefixes)} tasks")

    sessions = []
    seen_tasks: set[str] = set()

    for task_prefix in task_prefixes:
        # Extract task name from prefix
        parts = task_prefix.rstrip("/").split("/")
        task_name = parts[-1]

        # Deduplicate across runs (same task may appear in multiple runs)
        base_task = task_name.rsplit("__", 1)[0] if "__" in task_name else task_name
        if base_task in seen_tasks:
            continue
        seen_tasks.add(base_task)

        trajectory = download_trajectory(client, task_prefix)
        if trajectory is None:
            continue

        turns = extract_turns_from_trajectory(trajectory)
        if len(turns) < 2:
            continue

        sessions.append({
            "session_id": task_name,
            "source": source,
            "run": run_name,
            "num_turns": len(turns),
            "turns": turns,
        })

    print(f"  Extracted {len(sessions)} sessions (min 2 turns)")
    if sessions:
        turn_counts = [s["num_turns"] for s in sessions]
        print(f"  Turn distribution: min={min(turn_counts)}, median={sorted(turn_counts)[len(turn_counts)//2]}, max={max(turn_counts)}")

    return sessions


def main():
    parser = argparse.ArgumentParser(description="Download agent trajectories from GCS")
    parser.add_argument("--source", choices=["swebench", "terminalbench", "all"], default="all")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    sources = list(RUN_PREFIXES.keys()) if args.source == "all" else [args.source]

    print(f"Connecting to GCS bucket: {BUCKET_NAME}")
    client = storage.Client()

    for source in sources:
        print(f"\n{'='*60}")
        print(f"Processing {source} trajectories")
        print(f"{'='*60}")

        all_sessions = []
        for run_prefix in RUN_PREFIXES[source]:
            sessions = process_run(client, run_prefix, source)
            all_sessions.extend(sessions)

        # Deduplicate by session_id (keep first occurrence)
        seen = set()
        unique_sessions = []
        for s in all_sessions:
            if s["session_id"] not in seen:
                seen.add(s["session_id"])
                unique_sessions.append(s)

        output_path = args.output_dir / f"{source}_trajectories.jsonl"
        print(f"\nWriting {len(unique_sessions)} unique sessions to {output_path}")
        with open(output_path, "w") as f:
            for session in unique_sessions:
                f.write(json.dumps(session) + "\n")

        # Stats
        if unique_sessions:
            turn_counts = [s["num_turns"] for s in unique_sessions]
            print(f"Total sessions: {len(unique_sessions)}")
            print(f"Turn counts: min={min(turn_counts)}, median={sorted(turn_counts)[len(turn_counts)//2]}, max={max(turn_counts)}")
            print(f"Turn buckets:")
            for lo, hi, label in [(2, 5, "short (2-5)"), (5, 10, "medium (5-10)"), (10, 20, "long (10-20)"), (20, 100, "xl (20+)")]:
                count = sum(1 for t in turn_counts if lo <= t < hi)
                print(f"  {label}: {count} sessions")

    print("\nDone.")


if __name__ == "__main__":
    main()
