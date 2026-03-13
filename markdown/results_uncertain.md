# Benchmark Results — Client Location Uncertain (TTFT May Be Inflated)

> Results where the benchmark client location is uncertain. These runs may have been executed
> from ee-kraken connecting to a RunPod TCP port over the public internet, rather than from
> localhost on the same machine as the GPU.
>
> **TTFT WARNING**: If the client was on ee-kraken connecting to RunPod over TCP, TTFT values
> include round-trip network latency (typically 10-50ms per RTT depending on route) in addition
> to true prefill time. TPOT and throughput figures are unaffected by network RTT and remain valid.
> Do not compare TTFT from these runs directly against localhost runs in results_local.md.

---

## Server Config Legend

| Flag | Effect on metrics |
|------|------------------|
| `--enable-prefix-caching` | TTFT artificially low on file-based profiles (identical prompt → 100% cache hit after warmup). TTFT accurate on ShareGPT/random. |
| `--enable-chunked-prefill` | Improves throughput under load, no direct metric distortion |
| `--ignore-eos` | Required for FP8 models with random tokens — without it OSL hit rate is 37-51% |
| `--request-rate inf` (InferenceX) | Fires all requests instantly → TTFT inflated by queue buildup, not comparable to steady-concurrency TTFT |

---

## RunPod 1x H100 SXM — Llama 3.1 8B FP8

- Model: neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8
- Server: vLLM 0.17.0, **prefix caching ON, chunked prefill ON**
- GPU: 1x H100 SXM 80GB
- Tool: inference-benchmark (SSE streaming, real text, direct TCP)
- Date: 2026-03-10
- Client location: **uncertain** — may have been run from ee-kraken over RunPod TCP port

> ⚠️ **TTFT warning**: output-short/output-long use identical file prompts — prefix cache warms on first request, all subsequent TTFTs are near-zero prefill (cache hit). TTFT for these profiles is **not representative of real prefill cost**. TPOT and throughput are valid.
>
> ⚠️ **Network RTT warning**: if client was on ee-kraken, TTFT includes public internet RTT on top of prefill latency. TPOT and throughput are unaffected.

### output-short (~1200 tok input, max 128 tok output)

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | TPOT p99 | E2EL p50 |
|------|-------|-----------|-------------|----------|----------|----------|----------|----------|
| 1    | 1.85  | 222       | 2,589       | 57ms ⚠️  | 60ms     | 4.0ms    | 4.0ms    | 572ms    |
| 10   | 11.63 | 1,446     | 16,353      | 72ms ⚠️  | 2010ms   | 4.6ms    | 4.7ms    | 666ms    |
| 20   | 15.81 | 1,963     | 22,237      | 82ms ⚠️  | 187ms    | 6.1ms    | 26.9ms   | 867ms    |
| 40   | 36.56 | 4,322     | 51,186      | 122ms ⚠️ | 300ms    | 6.5ms    | 6.7ms    | 954ms    |
| 80   | 64.24 | 7,549     | 89,904      | 158ms ⚠️ | 324ms    | 7.4ms    | 7.6ms    | 1086ms   |
| 120  | 82.21 | 9,961     | 115,359     | 247ms ⚠️ | 439ms    | 7.6ms    | 8.1ms    | 1172ms   |
| 160  | 81.94 | 9,804     | 114,853     | 415ms ⚠️ | 733ms    | 9.2ms    | 9.7ms    | 1592ms   |

Throughput peaks at conc=120 (~82 req/s, ~10K output tok/s). TPOT stays 4.0–9.2ms.

### output-long (~180 tok input, max 1024 tok output)

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | TPOT p99 | E2EL p50  |
|------|-------|-----------|-------------|----------|----------|----------|----------|-----------|
| 1    | 0.24  | 243       | 296         | 58ms ⚠️  | 139ms    | 4.0ms    | 4.1ms    | 4,191ms   |
| 10   | 2.11  | 2,141     | 2,609       | 67ms ⚠️  | 113ms    | 4.6ms    | 4.6ms    | 4,732ms   |
| 20   | 3.73  | 3,815     | 4,642       | 77ms ⚠️  | 123ms    | 5.2ms    | 5.2ms    | 5,358ms   |
| 40   | 5.91  | 6,055     | 7,367       | 90ms ⚠️  | 151ms    | 5.5ms    | 5.6ms    | 5,739ms   |
| 80   | 7.67  | 7,850     | 9,552       | 183ms ⚠️ | 217ms    | 7.3ms    | 7.3ms    | 7,698ms   |
| 120  | 11.68 | 11,960    | 14,553      | 250ms ⚠️ | 279ms    | 8.1ms    | 8.1ms    | 8,521ms   |

Still scaling at conc=120. TPOT extremely consistent (4.0ms → 8.1ms).

### chatbot-short (ShareGPT real text, prefix cache ON, vLLM 0.17.1)

- Date: 2026-03-12
- Server: vLLM 0.17.1, **prefix caching ON, chunked prefill ON**, 1 GPU (tp=1)

> ✓ **TTFT valid for prefill** — ShareGPT varied prompts, no shared prefix across requests.
> ⚠️ **Network RTT warning**: if client was on ee-kraken, TTFT includes network latency on top of prefill.

| Conc | Req/s | In tok/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99   | TPOT p50 | TPOT p99 | E2EL p50 |
|------|-------|----------|-----------|-------------|----------|------------|----------|----------|----------|
| 1    | 1.02  | 177      | 234       | 411         | 21.0ms ✓ | 50.6ms     | 4.1ms    | 4.3ms    | 954ms    |
| 10   | 7.62  | 1,325    | 1,731     | 3,056       | 18.2ms ✓ | 1,982ms    | 4.4ms    | 4.5ms    | 1,054ms  |
| 20   | 10.72 | 1,865    | 2,477     | 4,342       | 20.2ms ✓ | 2,451ms    | 4.9ms    | 21.0ms   | 1,242ms  |
| 40   | 19.24 | 3,346    | 4,425     | 7,771       | 28.0ms ✓ | 110ms      | 5.2ms    | 5.3ms    | 1,229ms  |
| 80   | 24.69 | 4,294    | 5,633     | 9,926       | 51.8ms ✓ | 157ms      | 6.3ms    | 6.6ms    | 1,485ms  |
| 120  | 26.49 | 4,607    | 6,080     | 10,687      | 125.4ms ✓| 180ms      | 7.0ms    | 7.5ms    | 1,704ms  |

> ⚠️ TTFT p99 at conc=10 and conc=20 is very high (1.9-2.5s) — likely some requests hit warmup/scheduler contention. p50 is stable (18-20ms). Throughput scales well: 411 → 10,687 total tok/s.

**Key observations:**
- TPOT p50 @ conc=1: 4.1ms — **6.4x faster than A6000 bfloat16 (26.4ms)**
- Throughput peaks ~26 req/s at conc=120 with TPOT still only 7ms — not saturated
- TTFT p50 stays under 130ms all the way to conc=120

**A6000 vs H100 at concurrency=10, chatbot-short (TPOT only — TTFT not comparable across runs):**
| Metric | A6000 8B bfloat16 | H100 8B FP8 | Speedup |
|--------|-------------------|-------------|---------|
| Output tok/s | 273 | 1,731 | **6.3x** |
| TPOT p50 | 30.6ms | 4.4ms | **7.0x** |

---

**A6000 vs H100 at concurrency=10, output-short (TPOT only — TTFT not comparable):**
| Metric | A6000 8B bfloat16 | H100 8B FP8 | Speedup |
|--------|-------------------|-------------|---------|
| Output tok/s | 204 | 1,446 | **7.1x** |
| TPOT p50 | 45.7ms | 4.6ms | **9.9x** |

---

## RunPod 2x H100 SXM — Llama 3.1 70B FP8

- Model: neuralmagic/Meta-Llama-3.1-70B-Instruct-FP8
- Server: vLLM, tp=2, max_model_len=8192, **prefix caching OFF, chunked prefill OFF**
- GPU: 2x H100 SXM 80GB
- Tool: inference-benchmark (SSE streaming, real text, direct TCP)
- Date: 2026-03-11
- Client location: **uncertain** — may have been run from ee-kraken over RunPod TCP port

> TTFT here reflects **real prefill cost** (no prefix cache). File prompts still identical per profile but cache is disabled so each request pays full prefill.
>
> ⚠️ **Network RTT warning**: if client was on ee-kraken, TTFT includes public internet RTT on top of prefill latency. TPOT and throughput are unaffected.

### output-short (~1200 tok input, max 128 tok output)

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | TPOT p99 | E2EL p50 |
|------|-------|-----------|-------------|----------|----------|----------|----------|----------|
| 1    | 0.52  | 59        | 720         | 163ms    | 165ms    | 15.5ms   | 15.8ms   | 2,151ms  |
| 10   | 4.53  | 513       | 6,322       | 186ms    | 2,083ms  | 16.6ms   | 17.0ms   | 2,303ms  |
| 20   | 7.88  | 880       | 10,977      | 190ms    | 1,930ms  | 18.5ms   | 34.9ms   | 2,427ms  |
| 40   | 15.05 | 1,679     | 20,968      | 202ms    | 412ms    | 19.8ms   | 20.0ms   | 2,607ms  |
| 80   | 24.39 | 2,712     | 33,977      | 216ms    | 492ms    | 22.3ms   | 22.4ms   | 2,832ms  |
| 120  | 31.33 | 3,560     | 43,723      | 424ms    | 598ms    | 23.6ms   | 23.8ms   | 3,010ms  |

Throughput still scaling at conc=120. TPOT steady 15.5–23.6ms.

### output-long (~180 tok input, max 1024 tok output)

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | TPOT p99 | E2EL p50  |
|------|-------|-----------|-------------|----------|----------|----------|----------|-----------|
| 1    | 0.06  | 62        | 76          | 187ms    | 253ms    | 16.1ms   | 16.1ms   | 16,626ms  |
| 10   | 0.50  | 508       | 618         | 195ms    | 613ms    | 19.5ms   | 25.9ms   | 20,286ms  |
| 20   | 0.89  | 914       | 1,112       | 203ms    | 376ms    | 20.9ms   | 27.7ms   | 21,626ms  |
| 40   | 1.73  | 1,775     | 2,159       | 245ms    | 414ms    | 22.2ms   | 22.4ms   | 23,097ms  |
| 80   | 2.15  | 2,197     | 2,673       | 402ms    | 448ms    | 25.9ms   | 25.9ms   | 26,878ms  |
| 120  | 2.82  | 2,889     | 3,515       | 466ms    | 492ms    | 34.1ms   | 34.2ms   | 35,410ms  |

Still scaling at conc=120. TPOT jumps to 34.1ms at conc=120 — decode saturation.

---

## InferenceX vs inference-benchmark — 70B FP8 cross-validation

> ⚠️ **Client location uncertain** for inference-benchmark runs in this section. See section header above.

### Run 1 — Mar 10 (prefix caching ON, no --ignore-eos)

- Server: vLLM 0.17.0, 2x H100 SXM, **prefix caching ON, chunked prefill ON**
- Workload: random tokens ISL=1024, OSL=1024, **no --ignore-eos** → 70B FP8 only generates ~522 avg tokens (51% hit rate)
- 20-run averaged (10 runs each tool, alternated)

| Metric | inference-benchmark | InferenceX | Diff |
|--------|---------------------|------------|------|
| TTFT mean | 117.0ms | 149.8ms | ⚠️ 21.9% (RNG/cache difference) |
| TTFT p50 | 101.5ms | 144.1ms | ⚠️ 29.7% |
| TPOT mean | 16.39ms | 15.95ms | ✅ **2.7%** |

**TPOT matches within 2.7% — core decode speed validated.**

TTFT gap: InferenceX legacy RNG (`np.random.randint`) produces cache-hostile sequences → higher TTFT. Our `numpy.default_rng` produces tokens with better prefix cache hit rate → lower TTFT. Confirmed by running InferenceX's exact legacy RNG on our tool — TTFT jumped to 184ms.

### Run 2 — Mar 11 (prefix caching OFF, --ignore-eos)

- Server: vLLM, 2x H100 SXM, **prefix caching OFF**
- Workload: random tokens ISL=1024, OSL=1024, **--ignore-eos** → 100% OSL hit rate
- inference-benchmark: steady concurrency | InferenceX: `--request-rate inf` (all requests fired instantly)

| Conc | Tool | Workload | TPOT p50 | TTFT p50 | Out tok/s |
|------|------|----------|----------|----------|-----------|
| 10 | inference-benchmark | output-short (real text, OSL=128) | 16.6ms | 186ms | 513 |
| 10 | InferenceX | random (OSL=1024, ignore-eos) | 20.2ms | 340ms ⚠️ | 492 |
| 40 | inference-benchmark | output-short | 19.8ms | 202ms | 1,679 |
| 40 | InferenceX | random (OSL=1024, ignore-eos) | 23.0ms | 2,362ms ⚠️ | 1,343 |
| 80 | inference-benchmark | output-short | 22.3ms | 216ms | 2,712 |
| 80 | InferenceX | random (OSL=1024, ignore-eos) | 29.1ms | 2,927ms ⚠️ | 1,786 |

⚠️ InferenceX TTFT inflated by `--request-rate inf`. TPOT gap (~16-30%) is workload-driven: InferenceX runs OSL=1024 vs our OSL=128 → larger decode batches → higher TPOT. Not a tool error.

### --ignore-eos impact on 70B FP8 (conc=10, random ISL=1024 OSL=1024)

| Metric | Without `--ignore-eos` (Mar 10, prefix cache ON) | With `--ignore-eos` (Mar 11, prefix cache OFF) |
|--------|--------------------------------------------------|------------------------------------------------|
| Avg output tokens | ~522 / 1024 (51%) | 1024 / 1024 (100%) |
| TPOT mean | 15.95ms | 19.94ms (+25%) |
| TTFT p50 | 144ms | 340ms (⚠️ different server config) |

TPOT +25% with `--ignore-eos`: 2x more tokens in flight → denser decode batches → higher per-token latency. Use `--ignore-eos` for FP8 models — without it the GPU runs at ~50% of target decode load.

---

## Known issues with InferenceX's benchmark implementation

1. **Random tokens trigger EOS early on FP8 quantized models** — confirmed on both 8B FP8 (H100, 37% hit rate) and 70B FP8 (H100, 36-51% hit rate). 8B bfloat16 hits 1024/1024 (100%) — the issue is quantization, not model size.

   **Why**: FP8 (e4m3) uses 4-bit exponent + 3-bit mantissa vs bfloat16's 8+7. For natural language, strong semantic signal overwhelms quantization noise. For random OOD tokens, there is no coherent signal, so reduced precision distorts logits — and since EOS has high baseline probability in the original model, quantization errors systematically inflate its relative probability on OOD inputs. Result: early EOS termination on random token sequences.

   Use `--ignore-eos` when benchmarking any FP8/quantized model with random token workloads. Confirmed: `--ignore-eos` restores 100% OSL hit rate on 8B FP8.

2. **No failed request tracking** — failed requests silently return 0 tokens, skewing throughput numbers upward when server is overloaded.

3. **Prefix cache not accounted for** — repeat runs accumulate prefix cache hits, making TTFT appear lower over time. Results are not stationary.

4. **Double chat template (latent bug)** — with `--backend openai-chat --use-chat-template`, InferenceX pre-applies the chat template then sends formatted string as user message. vLLM applies template again. No significant TTFT impact on Llama 3.1 (confirmed experimentally) but semantically incorrect.

5. **Legacy numpy RNG produces cache-hostile sequences** — `np.random.randint(seed=0)` produces token sequences with lower prefix cache hit rates than `numpy.default_rng`. Makes TTFT appear ~30% higher than necessary.

6. **Only random synthetic workloads** — no real text, no multi-turn, no production profiles.

7. **`--request-rate inf` inflates TTFT** — fires all N requests at t=0, creating instant queue saturation. TTFT measures queue wait time + prefill, not just prefill. Use `--max-concurrency` with steady dispatch for comparable TTFT.

### Corrections to earlier claims

- ✅ **`--ignore-eos` IS used** — hardcoded in `benchmarks/benchmark_lib.sh` line 329. All official runs use it.
- ✅ **Prefix/radix cache IS disabled** — SGLang server launched with `--disable-radix-cache` in all FP8 benchmark scripts.
- ⚠️ **InferenceX official runs use SGLang, not vLLM** — server is `sglang.launch_server`. Our cross-validation used vLLM (`--backend openai-chat`). Different inference engines, so TPOT comparison has an additional variable beyond just the benchmark tool.

---

## inference-benchmark vs InferenceX

| Metric | inference-benchmark | InferenceX |
|---|---|---|
| TTFT | ✅ mean/p50/p90/p99 | ✅ p50/p90/p99 |
| TPOT / ITL | ✅ mean/p50/p90/p99 | ✅ |
| E2E latency | ✅ mean/p50/p90/p99 | ✅ |
| Failed request tracking | ✅ explicit count + errors | ❌ silent |
| Arrival pattern | ✅ steady + Poisson + ramp | Fixed rate only |
| Workload | ✅ Real text (91% OSL hit rate) | ❌ Synthetic random (51% on 70B FP8 without --ignore-eos) |
| ignore-eos support | ✅ --ignore-eos flag | ✅ --ignore-eos flag |
| Multi-backend | ✅ vLLM, SGLang, TRT-LLM | vLLM only |
| Multi-turn | ❌ Phase 2 | ❌ experimental stub only |

---

## What's missing for a complete picture

### 1. Saturation point on A6000 8B (local)
- **Status**: ✅ DONE — see results_local.md "A6000 Saturation point" section
- conc=80: TTFT bimodal (p50 ~125ms, p90 ~1.5-2.1s). conc=120: TTFT stable (p50 ~350ms, p90/p99 tight). Output tok/s still growing at conc=120 → GPU not fully saturated.

### 2. H100 70B FP8 — production profiles (RunPod)
- Model: neuralmagic/Meta-Llama-3.1-70B-Instruct-FP8
- Server: vLLM, tp=2, **--enable-prefix-caching --enable-chunked-prefill**, max_model_len ≥ 12000
- Profiles: chatbot-short, rag-retrieval, rag-heavy, coding-assist, summarization, agentic-tool-use
- Concurrency sweep: 1, 10, 20, 40, 80, 120
- **Why it matters**: production-scale model on real hardware — the headline benchmark

### 3. Multi-turn benchmarking (Phase 2)
- Not implemented yet — `src/modes/multi_turn.py` is a stub
- Need: `ConversationSession` sending growing message history across turns
- Key metric: TTFT at turn 1 vs turn N (should drop sharply with prefix caching)
- Expected result: TTFT at turn 2+ is ~5-10x lower than turn 1 (only new user message needs prefill)
- **Why it matters**: this is the main differentiator vs InferenceX — nobody else measures KV cache reuse

### 4. ISL/OSL distribution from real API logs
- Talk to Hannah/Ardo/Ze for logs from T2 Bench, SWE Bench, Terminal Bench
- Build synthetic profiles matching actual API traffic patterns
- **Why it matters**: current ShareGPT distribution may not match Sequrity.ai's actual workload

### 5. SGLang and TRT-LLM backends
- Currently only vLLM tested
- Need: SGLang (same radix cache, different scheduler), TRT-LLM (different API, estimated token counts)
- **Why it matters**: Aaron's plan requires vLLM vs SGLang vs TRT-LLM comparison

### 6. Docker images + pod setup script
- `scripts/pod_setup.sh [BRANCH]` — for existing RunPod images (SSH in, git clone, start benchmarking)
- `docker/Dockerfile.vllm` — FROM vllm/vllm-openai:latest, adds git+benchmark deps, entrypoint git clones at startup
- `docker/Dockerfile.sglang` — FROM lmsysorg/sglang:latest, same pattern
- `docker/Dockerfile.trtllm` — FROM nvcr.io/nvidia/tritonserver:24.12-trtllm-python-py3, same pattern
- Model weights NOT baked in — mount as network volume. Always pulls latest benchmark code via BENCH_BRANCH env var.
- **Status**: ✅ DONE — image `boothalgo01/bench-vllm:latest` pushed to Docker Hub. entrypoint.sh git clones sequrity-ai/inference-benchmark at container start, writes $PUBLIC_KEY to authorized_keys, starts sshd.
