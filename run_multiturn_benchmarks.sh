#!/usr/bin/env bash
# =============================================================================
# Multi-Turn Benchmark Orchestrator — All models × vLLM + SGLang
# Tests KV cache reuse with growing conversation context.
# Uses GPU parallelism: TP=1 runs 4 models at once, TP=2 runs 2.
#
# Usage: ./run_multiturn_benchmarks.sh [vllm|sglang|all]
#   Default: vllm
# =============================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-$(which python)}"
API_KEY="test"
WARMUP=3
TIMEOUT=300
CONC_SWEEP="1 5 10 20"
CONC_SWEEP_LOW="1 5 10"  # For memory-constrained configs
MAX_SERVER_WAIT=1800

# Multi-turn profiles to run
MT_PROFILES="chat-multiturn-short chat-multiturn-medium swebench-multiturn-short terminalbench-multiturn-short"

# Source the GPU scheduler
source "$REPO_ROOT/scripts/gpu_scheduler.sh"

log() { echo -e "\033[0;32m[MT-ORCH]\033[0m $1"; }
err() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }

# =============================================================================
# Model registry (models that work with prefix caching for multi-turn)
# =============================================================================
declare -a MODELS=(
    "Llama-3.1-8B|/workspace/models/Llama-3.1-8B-Instruct|1||--enable-chunked-prefill|32768|0.80"
    "Qwen3.5-9B|/workspace/models/Qwen3.5-9B|1|--trust-remote-code --disable-overlap-schedule|--enable-chunked-prefill --trust-remote-code --gdn-prefill-backend triton|32768|0.80"
    "Qwen3.5-27B|/workspace/models/Qwen3.5-27B|2|--trust-remote-code --disable-overlap-schedule|--enable-chunked-prefill --trust-remote-code --gdn-prefill-backend triton|16384|0.92"
    "Llama-3.1-70B|/workspace/models/Llama-3.1-70B-Instruct|2|--disable-piecewise-cuda-graph|--enable-chunked-prefill|4096|0.90"
)

model_exists() {
    local path="$1"
    [[ -d "$path" ]] && [[ -f "$path/config.json" ]] && ls "$path"/*.safetensors &>/dev/null
}

# =============================================================================
# Multi-turn benchmark callback — called by scheduler per model
# Args: engine, name, path, tp, port, slot_idx
# =============================================================================
mt_bench_callback() {
    local engine="$1" name="$2" path="$3" tp="$4" port="$5" slot_idx="$6"

    local tag="${name}_tp${tp}_${engine}"
    local run_date=$(date +%Y-%m-%d)
    local results_dir="results/${tag}/${run_date}"
    mkdir -p "$results_dir"

    local url="http://localhost:${port}/v1/chat/completions"

    # Select concurrency sweep
    local conc_list="$CONC_SWEEP"
    case "$name" in
        Llama-3.1-70B|Llama-3.3-70B|Qwen2.5-72B)
            conc_list="$CONC_SWEEP_LOW"
            slot_log "$slot_idx" "Low concurrency for $name TP=$tp (tight VRAM)"
            ;;
    esac

    for PROFILE in $MT_PROFILES; do
        slot_log "$slot_idx" "━━━ $name TP=$tp: $PROFILE ━━━"
        for CONC in $conc_list; do
            local out="${results_dir}/${PROFILE}_conc${CONC}.json"

            # Resume support
            if [[ -f "$out" ]] && [[ -s "$out" ]]; then
                completed=$("$PYTHON" -c "import json; d=json.load(open('$out')); print(d.get('num_requests_completed', d.get('completed_requests', d['summary'].get('successful_requests', 0))))" 2>/dev/null || echo "0")
                if [[ "$completed" -gt 0 ]]; then
                    slot_log "$slot_idx" "  SKIP conc=$CONC (exists, $completed reqs)"
                    continue
                else
                    slot_log "$slot_idx" "  Removing bad: $out"
                    rm -f "$out"
                fi
            fi

            slot_log "$slot_idx" "  $PROFILE conc=$CONC (multi-turn)"

            OPENAI_API_KEY="$API_KEY" "$PYTHON" -m src.benchmark.runner \
                --url        "$url" \
                --model      "$path" \
                --backend    "$engine" \
                --profile    "$PROFILE" \
                --concurrency "$CONC" \
                --mode       multi-turn \
                --warmup     "$WARMUP" \
                --timeout    "$TIMEOUT" \
                --api-key    "$API_KEY" \
                --output     "$out" \
                2>&1 || {
                    slot_log "$slot_idx" "  FAILED: $PROFILE conc=$CONC"
                }
        done
    done

    slot_log "$slot_idx" "Complete: $tag ($(find "$results_dir" -name "*multiturn*.json" -o -name "*swebench*.json" -o -name "*terminalbench*.json" 2>/dev/null | wc -l) multi-turn files)"
}

# =============================================================================
# Build job lists per TP level
# =============================================================================
run_engine() {
    local engine="$1"
    log ""
    log "╔══════════════════════════════════════════════════════════╗"
    log "║  Multi-Turn Sweep: $(printf '%-41s' "$engine (PARALLEL)")  ║"
    log "╚══════════════════════════════════════════════════════════╝"

    local -a tp1_jobs=()
    local -a tp2_jobs=()
    local -a tp4_jobs=()

    for model_spec in "${MODELS[@]}"; do
        IFS='|' read -r name path tp_list sglang_extra vllm_extra max_len gpu_mem <<< "$model_spec"

        if ! model_exists "$path"; then
            warn "SKIP $name — not found at $path"
            continue
        fi

        local job="${name}|${path}|${sglang_extra}|${vllm_extra}|${max_len}|${gpu_mem}"

        IFS=',' read -ra tps <<< "$tp_list"
        for tp in "${tps[@]}"; do
            case "$tp" in
                1) tp1_jobs+=("$job") ;;
                2) tp2_jobs+=("$job") ;;
                4) tp4_jobs+=("$job") ;;
            esac
        done
    done

    log "Job counts: TP=1: ${#tp1_jobs[@]}, TP=2: ${#tp2_jobs[@]}, TP=4: ${#tp4_jobs[@]}"

    if [[ ${#tp1_jobs[@]} -gt 0 ]]; then
        run_parallel_batch 1 "$engine" "mt_bench_callback" "${tp1_jobs[@]}"
    fi
    if [[ ${#tp2_jobs[@]} -gt 0 ]]; then
        run_parallel_batch 2 "$engine" "mt_bench_callback" "${tp2_jobs[@]}"
    fi
    if [[ ${#tp4_jobs[@]} -gt 0 ]]; then
        run_parallel_batch 4 "$engine" "mt_bench_callback" "${tp4_jobs[@]}"
    fi
}

# =============================================================================
# Main
# =============================================================================
TARGET="${1:-vllm}"

log "╔══════════════════════════════════════════════════════════╗"
log "║  MULTI-TURN BENCHMARK ORCHESTRATOR (PARALLEL)           ║"
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
    sglang) run_engine "sglang" ;;
    vllm)   run_engine "vllm" ;;
    all)    run_engine "vllm"; run_engine "sglang" ;;
    *)      echo "Usage: $0 [vllm|sglang|all]"; exit 1 ;;
esac

log ""
log "╔══════════════════════════════════════════════════════════╗"
log "║  MULTI-TURN BENCHMARKS COMPLETE                         ║"
log "╚══════════════════════════════════════════════════════════╝"
