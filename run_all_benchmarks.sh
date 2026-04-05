#!/usr/bin/env bash
# =============================================================================
# Master Benchmark Orchestrator — All models × SGLang + vLLM
# Runs production profiles with high concurrency sweep to find TPOT saturation.
#
# Usage: ./run_all_benchmarks.sh [sglang|vllm|all]
#   Default: all (SGLang first, then vLLM)
# =============================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-$(which python)}"
PORT=8000
API_KEY="test"
WARMUP=5
TIMEOUT=300
CONC_SWEEP="1 10 20 40 80 120 160"
CONC_SWEEP_LOW="1 10 20 40"  # For memory-constrained configs (tight KV budget)
PROFILES="chat-short chat-medium chat-long coding-agent prefill-heavy decode-heavy random-1k"
MAX_SERVER_WAIT=1800  # 30 min for large MoE models

log() { echo -e "\033[0;32m[ORCH]\033[0m $1"; }
err() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }

# =============================================================================
# Model registry: name, path, tp_configs, extra_sglang_flags, extra_vllm_flags
# =============================================================================
# 4x H100 SXM5 80GB (320GB total VRAM)
# TP configs based on weight size feasibility
declare -a MODELS=(
    # name|path|tp_list|sglang_extra|vllm_extra|max_model_len|gpu_mem
    # --- Small dense (TP=1,2,4) ---
    "Llama-3.1-8B|/workspace/models/Llama-3.1-8B-Instruct|1,2||--enable-chunked-prefill|32768|0.80"
    "Qwen3.5-9B|/workspace/models/Qwen3.5-9B|1,2|--trust-remote-code --disable-overlap-schedule|--enable-chunked-prefill --trust-remote-code --gdn-prefill-backend triton|32768|0.80"
    # --- Small MoE (TP=1,2) ---
    "gpt-oss-20b|/workspace/models/gpt-oss-20b|1,2||--enable-chunked-prefill|32768|0.80"
    # --- Medium dense (TP=2) ---
    "Qwen3.5-27B|/workspace/models/Qwen3.5-27B|2|--trust-remote-code --disable-overlap-schedule|--enable-chunked-prefill --trust-remote-code --gdn-prefill-backend triton|16384|0.92"
    # --- Medium MoE (TP=2 only — TP=1 OOMs: 80GB weights > single GPU usable VRAM) ---
    "gpt-oss-120b|/workspace/models/gpt-oss-120b|2||--enable-chunked-prefill|32768|0.80"
    # --- Large dense (TP=4 safe, TP=2 low-conc only) ---
    "Qwen2.5-72B|/workspace/models/Qwen2.5-72B-Instruct|4,2|--trust-remote-code --disable-piecewise-cuda-graph|--enable-chunked-prefill --trust-remote-code|4096|0.90"
    "Llama-3.1-70B|/workspace/models/Llama-3.1-70B-Instruct|4,2|--disable-piecewise-cuda-graph|--enable-chunked-prefill|4096|0.90"
    "Llama-3.3-70B|/workspace/models/Llama-3.3-70B-Instruct|4,2|--disable-piecewise-cuda-graph|--enable-chunked-prefill|4096|0.90"
    # --- Large MoE (TP=4) --- SKIPPED: GPUs 0,1 have leaked memory, only 2 GPUs available
    # "MiniMax-M2.5|/workspace/models/MiniMax-M2.5|4||--enable-chunked-prefill|8192|0.80"
    # GLM-4.6-FP8 skipped for now — 337GB weights may not fit 4x80GB
)

# =============================================================================
# Functions
# =============================================================================
kill_all_servers() {
    pkill -f "sglang.launch_server" 2>/dev/null || true
    pkill -f "vllm.entrypoints" 2>/dev/null || true
    sleep 5
    pkill -9 -f "sglang.launch_server" 2>/dev/null || true
    pkill -9 -f "vllm.entrypoints" 2>/dev/null || true
    sleep 3
}

wait_for_server() {
    local max_wait=$MAX_SERVER_WAIT
    local elapsed=0
    while ! curl -s "http://localhost:${PORT}/health" > /dev/null 2>&1; do
        sleep 5
        elapsed=$((elapsed + 5))
        if [ $elapsed -ge $max_wait ]; then
            return 1
        fi
        # Progress dot every 30s
        if (( elapsed % 30 == 0 )); then
            echo -n "."
        fi
    done
    echo ""
    log "Server ready after ${elapsed}s"
    return 0
}

model_exists() {
    local path="$1"
    [[ -d "$path" ]] && [[ -f "$path/config.json" ]] && ls "$path"/*.safetensors &>/dev/null
}

start_sglang_server() {
    local model_path="$1" tp="$2" extra_flags="$3" max_len="$4" gpu_mem="$5" tag="$6"

    local cmd="$PYTHON -m sglang.launch_server \
        --model-path $model_path \
        --tp $tp \
        --port $PORT \
        --dtype bfloat16 \
        --host 0.0.0.0 \
        --mem-fraction-static $gpu_mem \
        --context-length $max_len \
        --api-key $API_KEY"

    [[ -n "$extra_flags" ]] && cmd="$cmd $extra_flags"

    log "CMD: $cmd"
    eval $cmd > "/tmp/server_${tag}.log" 2>&1 &
    echo $!
}

start_vllm_server() {
    local model_path="$1" tp="$2" extra_flags="$3" max_len="$4" gpu_mem="$5" tag="$6"

    local cmd="$PYTHON -m vllm.entrypoints.openai.api_server \
        --model $model_path \
        --tensor-parallel-size $tp \
        --port $PORT \
        --dtype bfloat16 \
        --host 0.0.0.0 \
        --gpu-memory-utilization $gpu_mem \
        --max-model-len $max_len \
        --enable-prefix-caching \
        --api-key $API_KEY"

    [[ -n "$extra_flags" ]] && cmd="$cmd $extra_flags"

    log "CMD: $cmd"
    eval $cmd > "/tmp/server_${tag}.log" 2>&1 &
    echo $!
}

run_benchmark_suite() {
    local engine="$1" model_name="$2" model_path="$3" tp="$4" results_dir="$5" conc_list="$6"

    local url="http://localhost:${PORT}/v1/chat/completions"

    for PROFILE in $PROFILES; do
        log "  ━━━ Profile: $PROFILE ━━━"
        for CONC in $conc_list; do
            NREQ=200
            [[ "$CONC" -eq 1 ]] && NREQ=50
            [[ "$CONC" -ge 200 ]] && NREQ=150

            local out="${results_dir}/${PROFILE}_conc${CONC}.json"

            # Skip if valid result already exists (resume support)
            # Check both existence AND that num_requests_completed > 0
            if [[ -f "$out" ]] && [[ -s "$out" ]]; then
                completed=$("$PYTHON" -c "import json; d=json.load(open('$out')); print(d.get('num_requests_completed', d.get('completed_requests',0)))" 2>/dev/null || echo "0")
                if [[ "$completed" -gt 0 ]]; then
                    log "    SKIP conc=$CONC (already exists, $completed requests)"
                    continue
                else
                    warn "    Removing bad result file: $out (0 completed requests)"
                    rm -f "$out"
                fi
            fi

            log "    profile=$PROFILE conc=$CONC nreq=$NREQ"

            OPENAI_API_KEY="$API_KEY" "$PYTHON" -m src.benchmark.runner \
                --url        "$url" \
                --model      "$model_path" \
                --backend    "$engine" \
                --profile    "$PROFILE" \
                --concurrency "$CONC" \
                --num-requests "$NREQ" \
                --warmup     "$WARMUP" \
                --timeout    "$TIMEOUT" \
                --api-key    "$API_KEY" \
                --output     "$out" \
                2>&1 || {
                    err "    FAILED: $PROFILE conc=$CONC"
                }
        done
    done
}

run_engine() {
    local engine="$1"
    log ""
    log "╔══════════════════════════════════════════════════════════╗"
    log "║  Engine: $(printf '%-47s' "$engine")  ║"
    log "╚══════════════════════════════════════════════════════════╝"

    for model_spec in "${MODELS[@]}"; do
        IFS='|' read -r name path tp_list sglang_extra vllm_extra max_len gpu_mem <<< "$model_spec"

        if ! model_exists "$path"; then
            warn "SKIP $name — not found at $path"
            continue
        fi

        # SGLang: skip MXFP4 models (flashinfer tinygemm kernel broken with current CUDA)
        if [[ "$engine" == "sglang" ]]; then
            case "$name" in
                gpt-oss-20b|gpt-oss-120b)
                    warn "SKIP $name on SGLang — MXFP4 tinygemm kernel incompatible"
                    continue
                    ;;
            esac
        fi

        local run_date=$(date +%Y-%m-%d)
        IFS=',' read -ra tps <<< "$tp_list"
        for tp in "${tps[@]}"; do
            # SGLang: skip TP=4 for 70B+ models (CUDA illegal memory access in rc build)
            if [[ "$engine" == "sglang" && "$tp" -ge 4 ]]; then
                case "$name" in
                    Qwen2.5-72B|Llama-3.1-70B|Llama-3.3-70B)
                        warn "SKIP $name TP=$tp on SGLang — CUDA crash in 0.5.10rc0"
                        continue
                        ;;
                esac
            fi

            local tag="${name}_tp${tp}_${engine}"
            local results_dir="results/${tag}/${run_date}"
            mkdir -p "$results_dir"

            log ""
            log "══════════════════════════════════════════════════"
            log "  $engine | $name | TP=$tp"
            log "══════════════════════════════════════════════════"

            kill_all_servers

            # Start server
            local server_pid
            if [[ "$engine" == "sglang" ]]; then
                server_pid=$(start_sglang_server "$path" "$tp" "$sglang_extra" "$max_len" "$gpu_mem" "$tag")
            else
                server_pid=$(start_vllm_server "$path" "$tp" "$vllm_extra" "$max_len" "$gpu_mem" "$tag")
            fi
            log "Server PID: $server_pid"

            if ! wait_for_server; then
                err "Server failed to start for $tag. Last 20 lines:"
                tail -20 "/tmp/server_${tag}.log"
                kill_all_servers
                continue
            fi

            # Use low concurrency sweep for large dense models at TP=2 (tight KV budget)
            local conc_list="$CONC_SWEEP"
            case "$name" in
                Llama-3.1-70B|Llama-3.3-70B|Qwen2.5-72B)
                    if [[ "$tp" -le 2 ]]; then
                        conc_list="$CONC_SWEEP_LOW"
                        warn "Using low concurrency sweep for $name TP=$tp (tight VRAM)"
                    fi
                    ;;
            esac

            # Run all benchmarks
            run_benchmark_suite "$engine" "$name" "$path" "$tp" "$results_dir" "$conc_list"

            # Cleanup
            kill_all_servers
            log "DONE: $tag ($(ls "$results_dir"/*.json 2>/dev/null | wc -l) files)"
        done
    done
}

# =============================================================================
# Main
# =============================================================================
TARGET="${1:-all}"

log "╔══════════════════════════════════════════════════════════╗"
log "║  MASTER BENCHMARK ORCHESTRATOR                          ║"
log "║  4x NVIDIA H100 80GB — April 2026                      ║"
log "║  $(date)                        ║"
log "╚══════════════════════════════════════════════════════════╝"
log ""
log "Target:      $TARGET"
log "Concurrency: $CONC_SWEEP"
log "Profiles:    $PROFILES"
log ""

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo ""

case "$TARGET" in
    sglang)
        run_engine "sglang"
        ;;
    vllm)
        run_engine "vllm"
        ;;
    all)
        run_engine "sglang"
        run_engine "vllm"
        ;;
    *)
        echo "Usage: $0 [sglang|vllm|all]"
        exit 1
        ;;
esac

log ""
log "╔══════════════════════════════════════════════════════════╗"
log "║  ALL BENCHMARKS COMPLETE                                ║"
log "╚══════════════════════════════════════════════════════════╝"
log ""
log "Results summary:"
for d in results/*_sglang results/*_vllm; do
    [[ -d "$d" ]] || continue
    count=$(find "$d" -name "*.json" 2>/dev/null | wc -l)
    log "  $(basename "$d"): $count files"
done
