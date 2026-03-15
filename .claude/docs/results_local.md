# Benchmark Results — Local Runs (TTFT Valid)

> Results confirmed to be run with the benchmark client on the same machine as the GPU
> (localhost → localhost). TTFT values reflect true prefill latency with no network RTT component.

---

## Server Config Legend

| Flag | Effect on metrics |
|------|------------------|
| `--enable-prefix-caching` | TTFT artificially low on file-based profiles (identical prompt → 100% cache hit after warmup). TTFT accurate on ShareGPT/random. |
| `--enable-chunked-prefill` | Improves throughput under load, no direct metric distortion |
| `--ignore-eos` | Required for FP8 models with random tokens — without it OSL hit rate is 37-51% |
| `--request-rate inf` (InferenceX) | Fires all requests instantly → TTFT inflated by queue buildup, not comparable to steady-concurrency TTFT |

---

## RunPod 1x H100 SXM — Llama 3.1 8B FP8 — Production Profiles Sweep

- Model: neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8
- Server: vLLM 0.17.1, **prefix caching ON, chunked prefill ON**, tp=1
- GPU: 1x H100 SXM 80GB (RunPod)
- Tool: inference-benchmark (SSE streaming, ShareGPT real text)
- Date: 2026-03-12
- Client location: confirmed localhost (benchmark client ran on same RunPod pod as server)

> ✓ **TTFT valid** for all profiles — ShareGPT varied prompts, no shared prefix.

### chatbot-short

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | E2EL p50 |
|------|-------|-----------|-------------|----------|----------|----------|----------|
| 1    | 1.02  | 235       | 413         | 21.9ms   | 37.7ms   | 4.1ms    | 959ms    |
| 10   | 8.02  | 1,832     | 3,226       | 19.3ms   | 61.1ms   | 4.4ms    | 1,040ms  |
| 20   | 12.72 | 2,902     | 5,115       | 24.2ms   | 82.7ms   | 4.9ms    | 1,167ms  |
| 40   | 18.65 | 4,303     | 7,547       | 26.3ms   | 108ms    | 5.1ms    | 1,208ms  |
| 80   | 24.80 | 5,632     | 9,945       | 41.1ms   | 152ms    | 6.5ms    | 1,488ms  |
| 120  | 14.51 | 3,279     | 5,803       | 185.7ms  | 260ms    | 6.9ms    | 1,648ms  |

> ⚠️ conc=120 throughput dropped vs conc=80 — likely decode saturation at this ISL/OSL mix.

### chatbot-multi-turn

> Note: this is **single-turn mode** with larger ISL/OSL bounds (max 4000/1000 vs 2000/500 for chatbot-short) to simulate heavier conversation history. True multi-turn (growing KV cache across turns) is Phase 2.

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | E2EL p50 |
|------|-------|-----------|-------------|----------|----------|----------|----------|
| 1    | 0.79  | 236       | 403         | 22.8ms   | 82.2ms   | 4.1ms    | 1,149ms  |
| 10   | 6.28  | 1,878     | 3,204       | 20.9ms   | 64.7ms   | 4.4ms    | 1,246ms  |
| 20   | 9.89  | 2,982     | 5,071       | 23.9ms   | 79.1ms   | 5.0ms    | 1,412ms  |
| 40   | 15.28 | 4,550     | 7,778       | 26.7ms   | 105ms    | 5.2ms    | 1,491ms  |
| 80   | 19.32 | 5,875     | 9,955       | 48.3ms   | 143ms    | 6.6ms    | 1,936ms  |
| 120  | 21.66 | 6,457     | 11,033      | 150.7ms  | 247ms    | 7.4ms    | 2,172ms  |

### rag-retrieval

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | E2EL p50 |
|------|-------|-----------|-------------|----------|----------|----------|----------|
| 1    | 0.80  | 237       | 388         | 20.0ms   | 47.0ms   | 4.1ms    | 1,172ms  |
| 10   | 6.47  | 1,915     | 3,144       | 21.3ms   | 51.0ms   | 4.4ms    | 1,265ms  |
| 20   | 9.93  | 2,919     | 4,805       | 23.9ms   | 62.5ms   | 5.0ms    | 1,410ms  |
| 40   | 14.53 | 4,304     | 7,063       | 29.1ms   | 107ms    | 5.3ms    | 1,519ms  |
| 80   | 18.21 | 5,351     | 8,809       | 45.9ms   | 167ms    | 6.4ms    | 1,877ms  |
| 120  | 20.73 | 6,174     | 10,109      | 147.2ms  | 279ms    | 7.2ms    | 2,141ms  |

### rag-heavy

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | E2EL p50 |
|------|-------|-----------|-------------|----------|----------|----------|----------|
| 1    | 0.79  | 237       | 398         | 19.1ms   | 39.2ms   | 4.1ms    | 1,171ms  |
| 10   | 6.51  | 1,919     | 3,252       | 18.2ms   | 40.7ms   | 4.4ms    | 1,241ms  |
| 20   | 10.02 | 2,983     | 5,034       | 24.4ms   | 68.0ms   | 5.0ms    | 1,407ms  |
| 40   | 14.49 | 4,263     | 7,228       | 27.1ms   | 98.2ms   | 5.3ms    | 1,520ms  |
| 80   | 18.55 | 5,505     | 9,301       | 44.6ms   | 152ms    | 6.4ms    | 1,888ms  |
| 120  | 19.86 | 5,969     | 10,033      | 145.9ms  | 276ms    | 7.2ms    | 2,150ms  |

### coding-assist

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | E2EL p50 |
|------|-------|-----------|-------------|----------|----------|----------|----------|
| 1    | 0.81  | 237       | 402         | 18.1ms   | 32.7ms   | 4.1ms    | 1,130ms  |
| 10   | 6.38  | 1,924     | 3,230       | 18.7ms   | 52.9ms   | 4.4ms    | 1,268ms  |
| 20   | 10.04 | 3,001     | 5,056       | 20.3ms   | 61.8ms   | 5.0ms    | 1,411ms  |
| 40   | 14.52 | 4,285     | 7,256       | 26.3ms   | 93.9ms   | 5.2ms    | 1,485ms  |
| 80   | 18.12 | 5,403     | 9,110       | 47.0ms   | 148ms    | 6.5ms    | 1,857ms  |
| 120  | 19.69 | 5,904     | 9,934       | 148.9ms  | 277ms    | 7.3ms    | 2,196ms  |

### coding-heavy

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | E2EL p50 |
|------|-------|-----------|-------------|----------|----------|----------|----------|
| 1    | 0.80  | 238       | 401         | 16.9ms   | 27.3ms   | 4.1ms    | 1,156ms  |
| 10   | 6.46  | 1,902     | 3,224       | 18.3ms   | 47.3ms   | 4.4ms    | 1,235ms  |
| 20   | 10.13 | 2,960     | 5,034       | 20.2ms   | 56.4ms   | 5.0ms    | 1,400ms  |
| 40   | 14.48 | 4,285     | 7,248       | 26.9ms   | 94.6ms   | 5.2ms    | 1,495ms  |
| 80   | 17.95 | 5,381     | 9,054       | 46.1ms   | 155ms    | 6.5ms    | 1,928ms  |
| 120  | 20.39 | 6,044     | 10,216      | 173.3ms  | 202ms    | 7.2ms    | 2,146ms  |

### summarization

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | E2EL p50 |
|------|-------|-----------|-------------|----------|----------|----------|----------|
| 1    | 0.80  | 236       | 388         | 20.3ms   | 38.3ms   | 4.1ms    | 1,163ms  |
| 10   | 6.37  | 1,889     | 3,099       | 21.3ms   | 53.2ms   | 4.4ms    | 1,264ms  |
| 20   | 9.94  | 2,962     | 4,848       | 23.3ms   | 64.3ms   | 5.0ms    | 1,424ms  |
| 40   | 14.30 | 4,300     | 7,014       | 26.5ms   | 102ms    | 5.2ms    | 1,534ms  |
| 80   | 18.01 | 5,274     | 8,692       | 42.4ms   | 142ms    | 6.5ms    | 1,825ms  |
| 120  | 19.72 | 5,832     | 9,576       | 194.7ms  | 301ms    | 7.2ms    | 2,143ms  |

### agentic-tool-use

| Conc | Req/s | Out tok/s | Total tok/s | TTFT p50 | TTFT p99 | TPOT p50 | E2EL p50 |
|------|-------|-----------|-------------|----------|----------|----------|----------|
| 1    | 0.79  | 236       | 404         | 19.2ms   | 43.6ms   | 4.1ms    | 1,147ms  |
| 10   | 5.99  | 1,813     | 3,078       | 18.9ms   | 51.6ms   | 4.4ms    | 1,258ms  |
| 20   | 9.90  | 2,952     | 5,042       | 20.1ms   | 72.5ms   | 5.0ms    | 1,410ms  |
| 40   | 15.33 | 4,598     | 7,836       | 26.8ms   | 108ms    | 5.2ms    | 1,491ms  |
| 80   | 19.85 | 5,898     | 10,090      | 44.8ms   | 158ms    | 6.5ms    | 1,832ms  |
| 120  | 22.44 | 6,727     | 11,467      | 132.3ms  | 183ms    | 7.4ms    | 2,160ms  |

### Summary: TPOT p50 across all profiles (H100 8B FP8)

| Profile | conc=1 | conc=10 | conc=40 | conc=120 |
|---------|--------|---------|---------|----------|
| chatbot-short | 4.1ms | 4.4ms | 5.1ms | 6.9ms |
| chatbot-multi-turn | 4.1ms | 4.4ms | 5.2ms | 7.4ms |
| rag-retrieval | 4.1ms | 4.4ms | 5.3ms | 7.2ms |
| rag-heavy | 4.1ms | 4.4ms | 5.3ms | 7.2ms |
| coding-assist | 4.1ms | 4.4ms | 5.2ms | 7.3ms |
| coding-heavy | 4.1ms | 4.4ms | 5.2ms | 7.2ms |
| summarization | 4.1ms | 4.4ms | 5.2ms | 7.2ms |
| agentic-tool-use | 4.1ms | 4.4ms | 5.2ms | 7.4ms |

**TPOT is nearly identical across all production profiles** — decode speed on H100 depends only on concurrency/batch size, not ISL/OSL profile. Same pattern as A6000 but ~6-7x faster (4.1ms vs 27ms at conc=1).

**Peak output throughput**: ~6,700 tok/s at conc=120 (agentic-tool-use). All profiles still scaling at conc=120 — 8B FP8 on 1x H100 is not saturated.

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
