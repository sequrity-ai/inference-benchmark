# Next Steps — inference-benchmark

## What's done (Phase 1)

- [x] Git repo initialized with full directory structure
- [x] `src/benchmark/client.py` — async aiohttp SSE client, true TTFT parsing
- [x] `src/benchmark/metrics.py` — p50/p90/p99 for TTFT/TPOT/E2EL, separate input/output tok/s
- [x] `src/benchmark/runner.py` — async runner, semaphore concurrency, Poisson arrival, JSON output
- [x] `src/workloads/profiles.py` — 9 production workload profiles
- [x] `src/workloads/dataset.py` — ShareGPT + FileDataset (messages list format)
- [x] `src/workloads/arrival.py` — steady, Poisson, ramp arrival patterns
- [x] `configs/baseline_vllm_a6000.yaml` — baseline config
- [x] Tested against Llama 3.1 8B — works, 0 failures, correct metrics
- [x] Architect verified — duration bug fixed (warmup excluded from timing)

## What's done (Phase 1.5 — multi-backend)

- [x] `src/engines/openai_chat.py` — vLLM, SGLang, any OpenAI-compatible `/v1/chat/completions`
- [x] `src/engines/trtllm.py` — NVIDIA TRT-LLM `/generate_stream` (different request/response format)
- [x] `src/engines/__init__.py` — `get_backend(name)` factory, aliases: vllm/sglang/openai → openai_chat
- [x] `runner.py` updated — `--backend` flag, delegates to engine registry
- [x] `RequestResult` moved to `metrics.py` (shared across backends)
- [x] `scripts/bench.sh` — single profile run, all options as flags
- [x] `scripts/sweep.sh` — concurrency × profile matrix sweep, summary table
- [x] `scripts/smoke_test.sh` — quick 5-request sanity check
- [x] `scripts/check_server.sh` — health check, shows available models

### Backend usage

```bash
# vLLM or SGLang (OpenAI-compatible)
./scripts/bench.sh --backend vllm --url http://host:8000/v1/chat/completions

# SGLang (same endpoint, just alias)
./scripts/bench.sh --backend sglang --url http://host:8000/v1/chat/completions

# TRT-LLM
./scripts/bench.sh --backend trtllm --url http://host:8000/generate_stream
```

### Known TRT-LLM limitation
Token counts (tok/s) are estimated via word-split approximation — no tokenizer available
client-side. TTFT/TPOT/E2EL are accurate. Fix: pass `--tokenizer` path and use
`transformers.AutoTokenizer.apply_chat_template()` for both chat formatting and token counting.

---

## Phase 2: Multi-turn simulation (biggest differentiator)

`src/workloads/multi_turn.py`:
- `ConversationSession` — maintains message history, sends full context each turn
- `MultiTurnBenchmark` — orchestrates N concurrent sessions with think-time between turns
- Session profiles: quick-chat (3 turns), support-conversation (8 turns), coding-session (12 turns)
- Per-turn metrics: TTFT at turn 1 vs turn N (quantifies KV cache benefit)
- Requires prefix caching enabled on server (`--enable-prefix-caching`)

## Phase 2: Config-driven sweep runner

`src/benchmark/sweep.py`:
- Read YAML config, run `concurrency_sweep` × `workload_profiles` matrix
- Save each result as separate JSON with timestamp
- Print summary table at the end
- Support `num_runs > 1` for statistical significance

## Phase 2: Reporting

`src/reporting/charts.py`:
- Throughput vs latency Pareto curves (output tok/s vs p99 TTFT)
- TTFT distribution (CDF plot)
- TTFT by turn number (multi-turn cache benefit visualization)
- Uses plotly for interactive HTML charts

`src/reporting/html_report.py`:
- Jinja2 static HTML report from results JSON
- Embeds plotly charts

---

## Phase 3: RunPod / B200 baseline

- Run same benchmark profiles against B200 with Llama 3.1 70B (FP8)
- Compare vLLM vs TRT-LLM using `--backend` flag
- Run InferenceX on same hardware for official comparison numbers
- Publish results to `results/` with git tags

---

## Phase 4: Custom backend integration

- Add `src/engines/custom_engine.py` for Sequrity.ai prompt injection detection layer
- Security-specific metrics: detection latency, false positive rate, true positive rate
- `security-audit` workload profile with injection patterns

---

## Known issues / improvements

- [ ] TRT-LLM: add `--tokenizer` flag for accurate token counting + proper chat template
- [ ] Add warning when `usage` field absent (zero token counts in output)
- [ ] Implement `--config` flag to run full sweep from YAML (sweep.py)

---

## How to run

```bash
cd /home/khl22/inference/inference-benchmark

# Health check
./scripts/check_server.sh

# Smoke test (5 requests)
./scripts/smoke_test.sh

# Single profile
./scripts/bench.sh --profile output-long --concurrency 20 --num-requests 200

# Full sweep
./scripts/sweep.sh --profiles "output-short output-long chatbot-short" --concurrency "1 5 10 20 40"

# Poisson arrivals (direct)
OPENAI_API_KEY=test python -m src.benchmark.runner \
  --url http://localhost:8000/v1/chat/completions \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --profile chatbot-short \
  --concurrency 20 \
  --num-requests 200 \
  --arrival poisson \
  --target-rate 5.0 \
  --output results/chatbot_poisson.json
```
