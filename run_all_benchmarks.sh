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
CONC_SWEEP="1 10 20 40 80 120 160 200 256 320"
PROFILES="chat-short chat-medium chat-long coding-agent prefill-heavy decode-heavy"
MAX_SERVER_WAIT=1200  # 20 min for large models (72B/70B BF16 need >10min to load)

log() { echo -e "\033[0;32m[ORCH]\033[0m $1"; }
err() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }

# =============================================================================
# Model registry: name, path, tp_configs, extra_sglang_flags, extra_vllm_flags
# =============================================================================
# Small models: TP=1 and TP=2
# Large models: TP=2 only
# 70B/72B: reduced max_model_len to fit in VRAM at BF16
declare -a MODELS=(
    # name|path|tp_list|sglang_extra|vllm_extra|max_model_len|gpu_mem
    "Llama-3.1-8B|/workspace/models/Llama-3.1-8B-Instruct|1,2||--enable-chunked-prefill|32768|0.90"
    "Qwen3.5-9B|/workspace/models/Qwen3.5-9B|1,2|--trust-remote-code --disable-overlap-schedule|--enable-chunked-prefill --trust-remote-code|32768|0.90"
    "Qwen3.5-27B|/workspace/models/Qwen3.5-27B|2|--trust-remote-code --disable-overlap-schedule|--enable-chunked-prefill --trust-remote-code|16384|0.92"
    "Qwen2.5-72B|/workspace/models/Qwen2.5-72B-Instruct|2|--trust-remote-code|--enable-chunked-prefill --trust-remote-code|4096|0.95"
    "Llama-3.1-70B|/workspace/models/Llama-3.1-70B-Instruct|2||--enable-chunked-prefill|4096|0.95"
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
    local engine="$1" model_name="$2" model_path="$3" tp="$4" results_dir="$5"

    local url="http://localhost:${PORT}/v1/chat/completions"

    for PROFILE in $PROFILES; do
        log "  ━━━ Profile: $PROFILE ━━━"
        for CONC in $CONC_SWEEP; do
            NREQ=200
            [[ "$CONC" -eq 1 ]] && NREQ=50
            [[ "$CONC" -ge 200 ]] && NREQ=150

            local tag="${model_name}_tp${tp}_${engine}_${PROFILE}_conc${CONC}"
            local out="${results_dir}/${tag}.json"

            # Skip if already exists (resume support)
            if [[ -f "$out" ]] && [[ -s "$out" ]]; then
                log "    SKIP conc=$CONC (already exists)"
                continue
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

        IFS=',' read -ra tps <<< "$tp_list"
        for tp in "${tps[@]}"; do
            local tag="${name}_tp${tp}_${engine}"
            local results_dir="results/${tag}"
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

            # Run all benchmarks
            run_benchmark_suite "$engine" "$name" "$path" "$tp" "$results_dir"

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
log "║  2x NVIDIA H100 80GB — BF16 Full Precision             ║"
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
    count=$(ls "$d"/*.json 2>/dev/null | wc -l)
    log "  $(basename "$d"): $count files"
done
