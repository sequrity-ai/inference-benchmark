# Model Registry

## Downloaded Models

Stored at `/workspace/models/` on the RunPod network volume.

| Model | HF Repo | Size | TP Configs | Special Flags |
|-------|---------|------|:----------:|---------------|
| Llama-3.1-8B-Instruct | `meta-llama/Llama-3.1-8B-Instruct` | 30GB | 1, 2 | None |
| Llama-3.1-70B-Instruct | `meta-llama/Llama-3.1-70B-Instruct` | 217GB | 2 | `--max-model-len 4096 --gpu-mem 0.95` |
| Qwen3.5-9B | `Qwen/Qwen3.5-9B` | 19GB | 1, 2 | `--trust-remote-code --disable-overlap-schedule` (SGLang) |
| Qwen3.5-27B | `Qwen/Qwen3.5-27B` | 52GB | 2 | `--trust-remote-code --disable-overlap-schedule` (SGLang) |
| Qwen2.5-72B-Instruct | `Qwen/Qwen2.5-72B-Instruct` | 136GB | 2 | `--trust-remote-code --max-model-len 4096 --gpu-mem 0.95` |

## Access Requirements

| Model Family | Gated? | Notes |
|-------------|--------|-------|
| Llama 3.1 | Yes | HF license acceptance required per model |
| Llama 3.3 | Yes | Separate gate from 3.1 — `booth-algo` account does NOT have access |
| Qwen (all) | No | Open access |

## VRAM Planning (BF16 on 2x H100 80GB = 160GB total)

| Model | Weight Size | KV Budget | max_model_len | Feasible? |
|-------|:----------:|:---------:|:-------------:|:---------:|
| 8B TP=1 | ~16GB | ~64GB | 32768 | Yes |
| 8B TP=2 | ~16GB | ~144GB | 32768 | Yes |
| 9B TP=1 | ~18GB | ~62GB | 32768 | Yes |
| 27B TP=2 | ~52GB | ~108GB | 16384 | Yes |
| 72B TP=2 | ~136GB | ~24GB | 4096 | Tight |
| 70B TP=2 | ~140GB | ~20GB | 4096 | Tight |

For 70B+ with full context, use FP8 quantization (halves weight memory).

## Benchmark Matrix (from run_all_benchmarks.sh)

| Model | SGLang TP=1 | SGLang TP=2 | vLLM TP=1 | vLLM TP=2 |
|-------|:-----------:|:-----------:|:---------:|:---------:|
| Llama-3.1-8B | Done (50) | Done (50) | TODO | TODO |
| Qwen3.5-9B | Blocked | Blocked | TODO | TODO |
| Qwen3.5-27B | N/A | Empty | TODO | TODO |
| Qwen2.5-72B | N/A | Partial (25) | TODO | TODO |
| Llama-3.1-70B | N/A | TODO | TODO | TODO |
