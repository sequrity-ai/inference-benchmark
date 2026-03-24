# Server Management — vLLM & SGLang

## Launching vLLM

Use `scripts/launch_server.sh` for mode-aware launches:
```bash
# Single-turn mode (prefix caching ON)
CUDA_VISIBLE_DEVICES=0 ./scripts/launch_server.sh single-turn \
  --model /workspace/models/Llama-3.1-8B-Instruct \
  --tensor-parallel-size 1

# Stress-test mode (prefix caching OFF)
CUDA_VISIBLE_DEVICES=0 ./scripts/launch_server.sh stress-test \
  --model /workspace/models/Llama-3.1-8B-Instruct
```

### Defaults
- Port: 8000
- API key: `test`
- dtype: bfloat16
- GPU memory utilization: 0.75
- Max model len: 32768
- Logs: `/tmp/vllm_<mode>.log`

### Flags by Mode
| Mode | `--enable-prefix-caching` | `--enable-chunked-prefill` |
|------|:------------------------:|:--------------------------:|
| stress-test | NO | YES |
| single-turn | YES | YES |

## Launching SGLang

```bash
python -m sglang.launch_server \
  --model /workspace/models/Llama-3.1-8B-Instruct \
  --port 8000 \
  --tp 1 \
  --host 0.0.0.0
```

### Qwen3.5 Special Flags
Qwen3.5 (hybrid Gated Delta Net architecture) requires:
```bash
python -m sglang.launch_server \
  --model /workspace/models/Qwen3.5-9B \
  --trust-remote-code \
  --disable-overlap-schedule \
  ...
```

### CuDNN Fix for Qwen3.5
SGLang on Qwen3.5 requires CuDNN 9.15+:
```bash
pip install nvidia-cudnn-cu12==9.16.0.29
# OR
export SGLANG_DISABLE_CUDNN_CHECK=1
```

## Health Check

```bash
curl http://localhost:8000/health
```

## Killing Servers

```bash
# Graceful
pkill -f "sglang.launch_server"
pkill -f "vllm.entrypoints"

# Force (if graceful fails)
pkill -9 -f "sglang.launch_server"
pkill -9 -f "vllm.entrypoints"
```

`run_all_benchmarks.sh` handles server lifecycle automatically.

## Large Model VRAM Notes

70B/72B models at BF16 use ~136-140GB for weights on 2x80GB GPUs:

| Model | TP | max_model_len | gpu_mem | Notes |
|-------|:--:|:------------:|:-------:|-------|
| Llama 8B / Qwen 9B | 1 or 2 | 32768 | 0.90 | Fits easily |
| Qwen3.5 27B | 2 | 16384 | 0.92 | Moderate VRAM pressure |
| Qwen2.5 72B / Llama 70B | 2 | 4096 | 0.95 | Tight — <10GB/GPU for KV cache |

For 70B+ models, FP8 quantization or more GPUs recommended for full context windows.
