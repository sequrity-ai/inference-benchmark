# Benchmark Results

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

> ⚠️ **TTFT warning**: output-short/output-long use identical file prompts — prefix cache warms on first request, all subsequent TTFTs are near-zero prefill (cache hit). TTFT for these profiles is **not representative of real prefill cost**. TPOT and throughput are valid.

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

> TTFT here reflects **real prefill cost** (no prefix cache). File prompts still identical per profile but cache is disabled so each request pays full prefill.

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

## A6000 — Llama 3.1 8B bfloat16 baseline

- Model: meta-llama/Llama-3.1-8B-Instruct
- GPU: NVIDIA RTX A6000 (49GB VRAM), shared with other process (~6GB used)
- Server: vLLM, `--gpu-memory-utilization 0.75`, **prefix caching OFF**
- Tool: inference-benchmark (SSE streaming, true TTFT/TPOT/E2EL)
- Date: 2026-03-11

### output-short (ISL ~1200 tok, OSL max 128 tok — prefill-heavy)

| Concurrency | Req/s | In tok/s | Out tok/s | TTFT p50 | TTFT p99 | TPOT p50 | E2EL p99 |
|---|---|---|---|---|---|---|---|
| 1 | 0.29 | 368 | 35 | 237ms | 245ms | 26.5ms | 3657ms |
| 5 | 1.11 | 1427 | 133 | 243ms | 945ms | 34.8ms | 5165ms |
| 10 | 1.70 | 2182 | 204 | 246ms | 1890ms | 45.7ms | 6703ms |
| 20 | 2.45 | 3144 | 288 | 2133ms | 3637ms | 51.9ms | 8997ms |
| 40 | 2.99 | 3836 | 348 | 4819ms | 7335ms | 75.3ms | 14781ms |

### output-long (ISL ~180 tok, OSL max 1024 tok — decode-heavy)

| Concurrency | Req/s | In tok/s | Out tok/s | TTFT p50 | TTFT p99 | TPOT p50 | E2EL p99 |
|---|---|---|---|---|---|---|---|
| 1 | 0.04 | 8 | 38 | 73ms | 79ms | 26.4ms | 27199ms |
| 5 | 0.17 | 38 | 177 | 199ms | 203ms | 27.9ms | 29207ms |
| 10 | 0.32 | 72 | 324 | 329ms | 358ms | 30.0ms | 31096ms |
| 20 | 0.51 | 112 | 518 | 535ms | 692ms | 32.4ms | 33860ms |
| 40 | 0.72 | 159 | 734 | 1302ms | 1304ms | 36.5ms | 38701ms |

### chatbot-short (ShareGPT real text, ISL ~200 tok, OSL ~150 tok)

| Concurrency | Req/s | In tok/s | Out tok/s | TTFT p50 | TTFT p99 | TPOT p50 | E2EL p99 |
|---|---|---|---|---|---|---|---|
| 1 | 0.26 | 79 | 36 | 61ms | 310ms | 26.4ms | 4341ms |
| 5 | 1.15 | 320 | 158 | 71ms | 633ms | 28.8ms | 4938ms |
| 10 | 1.96 | 546 | 273 | 215ms | 763ms | 30.6ms | 5274ms |
| 20 | 3.16 | 880 | 439 | 607ms | 1128ms | 33.1ms | 6138ms |
| 40 | 4.53 | 1259 | 621 | 1003ms | 1854ms | 36.9ms | 7398ms |

**Key observations:**
- TPOT baseline ~26ms at conc=1 across all profiles (decode speed for 8B bfloat16 on A6000)
- output-short TTFT flat up to conc=10, spikes hard at conc=20 (prefill queue saturation)
- chatbot-short scales best — short ISL/OSL, TTFT under 70ms up to conc=5
- ShareGPT OSL hit rate: 91-93% (avg ~138 tok vs target 150) — real text behaves well

---

## A6000 — Llama 3.1 8B bfloat16 — single-turn mode (ShareGPT natural distribution)

- Model: meta-llama/Llama-3.1-8B-Instruct (bfloat16)
- GPU: NVIDIA RTX A6000 (48GB), shared with other process (~6GB used)
- Server: vLLM, `--enable-prefix-caching`, `--enable-chunked-prefill`, `--gpu-memory-utilization 0.75`, `max_model_len=32768`
- Tool: inference-benchmark (SSE streaming, true TTFT/TPOT/E2EL)
- Profile: chatbot-short — **ShareGPT natural ISL/OSL distribution** (max_isl=2000, max_osl=500)
- Date: 2026-03-12

> ✓ **TTFT valid** — ShareGPT prompts are varied across requests (no shared prefix → no cache hit effect on TTFT).
> This is the **single-turn mode** baseline: server uses full context window (32768), not ISL+OSL+margin.
> ISL/OSL are not fixed — each request gets the natural conversation length from ShareGPT.

**Token distribution (natural ShareGPT, not fixed targets):**
- ISL: min=42, median=65, max=1,656 tokens
- OSL: min=10, median=220, max=479 tokens
- OSL distribution: <50tok (11%), 50-150tok (20%), 150-300tok (45%), 300-500tok (24%)

### chatbot-short (ShareGPT natural distribution, prefix cache ON)

| Conc | Req/s | In tok/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | TPOT p99 | E2EL p50 |
|------|-------|----------|-----------|-------------|----------|----------|----------|----------|----------|
| 1    | 0.17  | 40       | 36        | 75          | 59ms ✓   | 276ms    | 27.3ms   | 27.7ms   | 5,778ms  |
| 10   | 1.37  | 287      | 294       | 581         | 64ms ✓   | 154ms    | 30.6ms   | 32.5ms   | 7,041ms  |
| 20   | 2.15  | 374      | 492       | 866         | 74ms ✓   | 149ms    | 34.9ms   | 42.0ms   | 8,224ms  |
| 40   | 3.48  | 605      | 796       | 1,402       | 80ms ✓   | 221ms    | 38.4ms   | 43.0ms   | 8,854ms  |
| 80   | —     | —        | 1,117     | —           | 123ms ✓  | 2,228ms  | 46.4ms   | —        | —        |
| 120  | —     | —        | 1,502     | —           | 319ms ✓  | 404ms    | 44.9ms   | —        | —        |

> ⚠️ **TTFT p90 at conc=80: 2,062ms** — bimodal distribution. Some requests hit scheduler queue (p90 spikes); p50 still 123ms. At conc=120, queue drains faster (p50=319ms, p90/p99 tight at 401/404ms). Output tok/s still growing: 796 → 1,117 → 1,502.

**vs previous A6000 chatbot-short (prefix cache OFF, fixed OSL=150):**
| Metric | Cache OFF (Mar-11) | Cache ON, natural OSL (Mar-12) | Notes |
|--------|-------------------|-------------------------------|-------|
| TTFT p50 @ conc=10 | 215ms | 64ms | Cache warms system prompt prefix; TTFT drops |
| TPOT p50 @ conc=10 | 30.6ms | 30.6ms | Identical — decode speed unaffected by caching |
| Out tok/s @ conc=10 | 273 | 294 | ~8% higher — natural OSL avg ~214 vs fixed 150 |
| TTFT p50 @ conc=40 | 1,003ms | 80ms | **12x lower TTFT** with prefix caching ON |

**Key observations:**
- TTFT with prefix cache ON is dramatically lower at high concurrency (80ms vs 1,003ms at conc=40) — system prompt prefix is cached after warmup, only user message needs prefill
- TPOT unchanged by prefix caching (as expected — decode is not affected)
- Natural OSL mean ~210 tokens vs fixed 150 → throughput numbers reflect realistic session lengths
- TTFT stays flat 59-80ms across conc=1 to conc=40 — very stable scheduling under prefix cache

---

## A6000 — Llama 3.1 8B bfloat16 — single-turn mode (additional profiles)

- Model: meta-llama/Llama-3.1-8B-Instruct (bfloat16)
- GPU: NVIDIA RTX A6000 (48GB), shared (~6GB other process)
- Server: vLLM, `--enable-prefix-caching`, `--enable-chunked-prefill`, `--gpu-memory-utilization 0.75`, `max_model_len=32768`
- Tool: inference-benchmark
- Date: 2026-03-12

### rag-retrieval (ShareGPT natural distribution, max_isl=6000, max_osl=1000, prefix cache ON)

> ✓ **TTFT valid** — ShareGPT varied prompts, no shared prefix across requests.

| Conc | Req/s | In tok/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | TPOT p99 | E2EL p50 |
|------|-------|----------|-----------|-------------|----------|----------|----------|----------|----------|
| 1    | 0.12  | 21       | 34        | 56          | 60ms ✓   | 183ms    | 27.9ms   | 28.7ms   | 7,848ms  |
| 10   | 1.00  | 193      | 278       | 472         | 64ms ✓   | 284ms    | 30.7ms   | 34.1ms   | 7,847ms  |
| 20   | 1.67  | 349      | 488       | 838         | 68ms ✓   | 251ms    | 33.4ms   | 38.2ms   | 9,458ms  |
| 40   | 2.53  | 529      | 754       | 1,284       | 76ms ✓   | 167ms    | 37.0ms   | 38.9ms   | 10,385ms |
| 80   | —     | —        | 995       | —           | 132ms ✓  | 2,277ms  | 49.7ms   | —        | —        |
| 120  | —     | —        | 1,214     | —           | 396ms ✓  | 465ms    | 48.7ms   | —        | —        |

> ⚠️ **TTFT p90 at conc=80: 1,443ms** — same bimodal pattern as chatbot-short. At conc=120, p90 snaps to 458ms. Output tok/s still growing: 754 → 995 → 1,214.

### output-short (file prompt, ISL ~1200 tok, OSL max 128 tok, prefix cache ON)

> ⚠️ **TTFT NOT valid** — identical file prompt, prefix cache ON → 100% cache hit after warmup. TPOT and throughput valid.

| Conc | Req/s | In tok/s | Out tok/s | Total tok/s | TTFT p50   | TTFT p99  | TPOT p50 | TPOT p99 | E2EL p50 |
|------|-------|----------|-----------|-------------|------------|-----------|----------|----------|----------|
| 1    | 0.32  | 412      | 35        | 447         | 57ms ⚠️   | 190ms     | 27.5ms   | 28.2ms   | 3,575ms  |
| 10   | 2.54  | 3,255    | 298       | 3,553       | 66ms ⚠️   | 94ms      | 31.1ms   | 31.9ms   | 4,043ms  |
| 20   | 4.68  | 6,006    | 550       | 6,556       | 72ms ⚠️   | 132ms     | 33.7ms   | 34.1ms   | 4,385ms  |
| 40   | 7.94  | 10,179   | 932       | 11,111      | 96ms ⚠️   | 192ms     | 37.1ms   | 37.4ms   | 4,856ms  |

**vs cache OFF (Mar-11):** TPOT p50 at conc=10: 45.7ms → 31.1ms (32% lower — chunked prefill + cache reduces scheduling contention)

### output-long (file prompt, ISL ~180 tok, OSL max 1024 tok, prefix cache ON)

> ⚠️ **TTFT NOT valid** — identical file prompt, prefix cache ON → 100% cache hit after warmup. TPOT and throughput valid.

| Conc | Req/s | In tok/s | Out tok/s | Total tok/s | TTFT p50   | TTFT p99  | TPOT p50 | TPOT p99 | E2EL p50  |
|------|-------|----------|-----------|-------------|------------|-----------|----------|----------|-----------|
| 1    | 0.04  | 7        | 35        | 43          | 56ms ⚠️   | 61ms      | 27.8ms   | 28.0ms   | 28,558ms  |
| 10   | 0.31  | 68       | 315       | 384         | 66ms ⚠️   | 73ms      | 31.5ms   | 31.8ms   | 32,283ms  |
| 20   | 0.54  | 120      | 556       | 677         | 106ms ⚠️  | 126ms     | 33.8ms   | 34.1ms   | 34,680ms  |
| 40   | 0.97  | 215      | 994       | 1,210       | 152ms ⚠️  | 187ms     | 38.1ms   | 38.2ms   | 39,202ms  |

---

## A6000 — Saturation point (conc=80/120, single-turn mode)

- Date: 2026-03-12
- Same server config as single-turn mode above (prefix cache ON, chunked prefill ON, 0.75 GMU)

| Profile | Conc | Out tok/s | TTFT p50 | TTFT p90 | TTFT p99 | TPOT p50 |
|---------|------|-----------|----------|----------|----------|----------|
| chatbot-short | 40  | 796   | 80ms ✓   | —        | 221ms    | 38.4ms   |
| chatbot-short | 80  | 1,117 | 123ms ✓  | 2,062ms  | 2,228ms  | 46.4ms   |
| chatbot-short | 120 | 1,502 | 319ms ✓  | 401ms    | 404ms    | 44.9ms   |
| rag-retrieval | 40  | 754   | 76ms ✓   | —        | 167ms    | 37.0ms   |
| rag-retrieval | 80  | 995   | 132ms ✓  | 1,443ms  | 2,277ms  | 49.7ms   |
| rag-retrieval | 120 | 1,214 | 396ms ✓  | 458ms    | 465ms    | 48.7ms   |

**Key observations:**
- Output tok/s is still growing at conc=120 — A6000 8B is NOT saturated at 120 concurrent requests
- TTFT at conc=80 shows a **bimodal distribution**: p50 is 123-132ms (fast path) but p90 jumps to 1.4-2.1s (slow path — requests hit prefill queue behind large decode batch). This is the scheduling interference zone.
- At conc=120 the bimodal effect disappears: p50/p90/p99 collapse (319/401/404ms) — the scheduler is continuously busy, queue wait is predictable
- TPOT at conc=80-120 is 44-50ms (vs 26ms at conc=1) — decode batches are large, memory bandwidth saturating
- **Practical saturation**: conc=80 is the worst operating point (high variance TTFT). conc=40 is the sweet spot (sub-100ms TTFT p50, TPOT 37-38ms). conc=120 recovers variance but TTFT rises to 320-400ms range.

**TPOT summary — A6000 8B bfloat16 single-turn (cache ON, chunked prefill ON):**
| Profile | TPOT p50 @ conc=1 | TPOT p50 @ conc=10 | TPOT p50 @ conc=40 |
|---------|-------------------|--------------------|--------------------|
| chatbot-short (ShareGPT) | 27.3ms | 30.6ms | 38.4ms |
| rag-retrieval (ShareGPT) | 27.9ms | 30.7ms | 37.0ms |
| output-short (file)      | 27.5ms | 31.1ms | 37.1ms |
| output-long (file)       | 27.8ms | 31.5ms | 38.1ms |

TPOT is consistent across profiles — decode speed depends on concurrency/batch size, not ISL/OSL profile.

---

## A6000 — Llama 3.1 8B bfloat16 — stress-test mode (random tokens, --ignore-eos)

- Model: meta-llama/Llama-3.1-8B-Instruct (bfloat16)
- GPU: NVIDIA RTX A6000 (48GB), shared (~6GB other process)
- Server: vLLM, **prefix caching OFF**, `--enable-chunked-prefill`, `--gpu-memory-utilization 0.75`, `max_model_len=32768`
- Profile: random-inferencex — ISL=1024, OSL=1024 random tokens
- Client flags: `--ignore-eos` (bfloat16 doesn't need it for OSL correctness, but used for consistency with FP8 cross-validation methodology)
- Tool: inference-benchmark
- Date: 2026-03-12

> ✗ **TTFT NOT comparable to InferenceX** — we use steady semaphore concurrency; InferenceX uses `--request-rate inf` (fires all requests at t=0, inflating TTFT with queue wait). **Compare TPOT only.**

### random-inferencex (ISL=1024, OSL=1024, --ignore-eos, prefix cache OFF)

| Conc | Req/s | In tok/s | Out tok/s | TTFT p50  | TTFT p99  | TPOT p50 | TPOT p99 | E2EL p50  |
|------|-------|----------|-----------|-----------|-----------|----------|----------|-----------|
| 1    | 0.03  | 36       | 34        | 219ms ✗   | 284ms     | 28.6ms   | 28.9ms   | 29,532ms  |
| 10   | 0.27  | 292      | 280       | 453ms ✗   | 1,213ms   | 34.1ms   | 35.0ms   | 35,379ms  |
| 40   | 0.63  | 668      | 640       | 1,004ms ✗ | 6,719ms   | 50.5ms   | 52.3ms   | 53,714ms  |
| 80   | 0.75  | 796      | 763       | 5,674ms ✗ | 14,444ms  | 72.7ms   | 75.7ms   | 83,009ms  |

**Key observations:**
- TPOT p50 @ conc=1: 28.6ms — matches single-turn baseline (27-28ms) as expected
- TPOT degrades at high concurrency: 28.6ms → 72.7ms at conc=80 (1024 tok output batches are memory-bandwidth heavy)
- TTFT rises sharply — at conc=40+ the prefill queue saturates (1024 tok input × 40 concurrent = 40k tokens in flight simultaneously)
- OSL hit rate: ~100% (bfloat16 + --ignore-eos → model generates exactly 1024 tokens per request)

**stress-test vs single-turn TPOT comparison (A6000 8B bfloat16):**
| Conc | Single-turn chatbot-short TPOT p50 | Stress-test random-1024 TPOT p50 | Delta |
|------|-----------------------------------|----------------------------------|-------|
| 1    | 27.3ms                            | 28.6ms                           | +5%   |
| 10   | 30.6ms                            | 34.1ms                           | +11%  |
| 40   | 38.4ms                            | 50.5ms                           | +31%  |

Random 1024-token output batches are significantly heavier than natural ShareGPT output (~220 tok avg) at high concurrency — batch memory pressure is the primary driver.

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
- **Status**: ✅ DONE — see "A6000 Saturation point" section above
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
- **Status**: ✅ DONE — push repo to GitHub first (entrypoint.sh git clones sequrity-ai/inference-benchmark), then `docker build -f docker/Dockerfile.vllm -t sequrity/bench-vllm:latest .`
