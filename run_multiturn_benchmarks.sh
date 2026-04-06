#!/usr/bin/env bash
# =============================================================================
# Multi-Turn Benchmark Orchestrator — All models × vLLM + SGLang
# Tests KV cache reuse with growing conversation context.
# Server MUST have prefix caching enabled.
#
# Usage: ./run_multiturn_benchmarks.sh [vllm|sglang|all]
#   Default: vllm
# =============================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-$(which python)}"
PORT=8000
API_KEY="test"
WARMUP=3
TIMEOUT=300
CONC_SWEEP="1 5 10 20"
CONC_SWEEP_LOW="1 5 10"  # For memory-constrained configs
MAX_SERVER_WAIT=1800

# Multi-turn profiles to run
MT_PROFILES="chat-multiturn-short chat-multiturn-medium swebench-multiturn-short terminalbench-multiturn-short"

log() { echo -e "\033[0;32m[MT-ORCH]\033[0m $1"; }
err() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }

# =============================================================================
# Model registry (same as single-turn but only models that fit with prefix caching)
# =============================================================================
declare -a MODELS=(
    # name|path|tp_list|sglang_extra|vllm_extra|max_model_len|gpu_mem
    "Llama-3.1-8B|/workspace/models/Llama-3.1-8B-Instruct|1||--enable-chunked-prefill|32768|0.80"
    "Qwen3.5-9B|/workspace/models/Qwen3.5-9B|1|--trust-remote-code --disable-overlap-schedule|--enable-chunked-prefill --trust-remote-code --gdn-prefill-backend triton|32768|0.80"
    "Qwen3.5-27B|/workspace/models/Qwen3.5-27B|2|--trust-remote-code --disable-overlap-schedule|--enable-chunked-prefill --trust-remote-code --gdn-prefill-backend triton|16384|0.92"
    "Llama-3.1-70B|/workspace/models/Llama-3.1-70B-Instruct|2|--disable-piecewise-cuda-graph|--enable-chunked-prefill|4096|0.90"
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

run_multiturn_suite() {
    local engine="$1" model_name="$2" model_path="$3" tp="$4" results_dir="$5" conc_list="$6"
    local url="http://localhost:${PORT}/v1/chat/completions"

    for PROFILE in $MT_PROFILES; do
        log "  ━━━ Profile: $PROFILE ━━━"
        for CONC in $conc_list; do
            local out="${results_dir}/${PROFILE}_conc${CONC}.json"

            # Skip if valid result already exists
            if [[ -f "$out" ]] && [[ -s "$out" ]]; then
                completed=$("$PYTHON" -c "import json; d=json.load(open('$out')); print(d.get('num_requests_completed', d.get('completed_requests', d['summary'].get('successful_requests', 0))))" 2>/dev/null || echo "0")
                if [[ "$completed" -gt 0 ]]; then
                    log "    SKIP conc=$CONC (already exists, $completed requests)"
                    continue
                else
                    warn "    Removing bad result file: $out (0 completed requests)"
                    rm -f "$out"
                fi
            fi

            log "    profile=$PROFILE conc=$CONC (multi-turn)"

            OPENAI_API_KEY="$API_KEY" "$PYTHON" -m src.benchmark.runner \
                --url        "$url" \
                --model      "$model_path" \
                --backend    "$engine" \
                --profile    "$PROFILE" \
                --concurrency "$CONC" \
                --mode       multi-turn \
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
    log "║  Multi-Turn Sweep: $(printf '%-41s' "$engine")  ║"
    log "╚══════════════════════════════════════════════════════════╝"

    for model_spec in "${MODELS[@]}"; do
        IFS='|' read -r name path tp_list sglang_extra vllm_extra max_len gpu_mem <<< "$model_spec"

        if ! model_exists "$path"; then
            warn "SKIP $name — not found at $path"
            continue
        fi

        # SGLang: skip MXFP4 and TP=4 (same as single-turn)
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
            local tag="${name}_tp${tp}_${engine}_mt"
            local results_dir="results/${name}_tp${tp}_${engine}/${run_date}"
            mkdir -p "$results_dir"

            log ""
            log "══════════════════════════════════════════════════"
            log "  $engine | $name | TP=$tp | MULTI-TURN"
            log "══════════════════════════════════════════════════"

            kill_all_servers

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

            # Use low concurrency for 70B models
            local conc_list="$CONC_SWEEP"
            case "$name" in
                Llama-3.1-70B|Llama-3.3-70B|Qwen2.5-72B)
                    conc_list="$CONC_SWEEP_LOW"
                    warn "Using low concurrency sweep for $name TP=$tp (tight VRAM)"
                    ;;
            esac

            run_multiturn_suite "$engine" "$name" "$path" "$tp" "$results_dir" "$conc_list"

            kill_all_servers
            log "DONE: $tag ($(find "$results_dir" -name "*multiturn*.json" -o -name "*swebench*.json" -o -name "*terminalbench*.json" 2>/dev/null | wc -l) multi-turn files)"
        done
    done
}

# =============================================================================
# Main
# =============================================================================
TARGET="${1:-vllm}"

log "╔══════════════════════════════════════════════════════════╗"
log "║  MULTI-TURN BENCHMARK ORCHESTRATOR                      ║"
log "║  4x NVIDIA H100 80GB — $(date +%B\ %Y)                     ║"
log "║  $(date)                        ║"
log "╚══════════════════════════════════════════════════════════╝"
log ""
log "Target:      $TARGET"
log "Concurrency: $CONC_SWEEP"
log "Profiles:    $MT_PROFILES"
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
        run_engine "vllm"
        run_engine "sglang"
        ;;
    *)
        echo "Usage: $0 [vllm|sglang|all]"
        exit 1
        ;;
esac

log ""
log "╔══════════════════════════════════════════════════════════╗"
log "║  MULTI-TURN BENCHMARKS COMPLETE                         ║"
log "╚══════════════════════════════════════════════════════════╝"
