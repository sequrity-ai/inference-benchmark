"""
Workload profile definitions.

Based on real-world LLM usage patterns from OpenRouter 100T token study
and NVIDIA benchmarking guidance. Each profile defines typical ISL/OSL,
a description, and the data source to use.
"""

from dataclasses import dataclass
from typing import Optional


# Valid tag values (for documentation and validation)
AGENT_TYPES = ["chat", "coding", "computer-use", "customer-support"]
TURN_STYLES = ["single-turn", "multi-turn"]
SERVING_STYLES = ["disaggregated", "not-disaggregated"]
DATA_SOURCES = ["sharegpt", "swebench", "terminalbench", "file", "random", "test"]


@dataclass
class WorkloadProfile:
    name: str
    isl_tokens: int   # for random: exact target ISL; for sharegpt: max ISL filter bound
    osl_tokens: int   # for random: exact target OSL; for sharegpt: max OSL filter bound (also max_tokens)
    isl_stddev: float        # stddev as fraction of isl (for Gaussian sampling)
    description: str
    dataset: str             # "sharegpt", "file", "test", "random"
    file_path: str = ""      # used when dataset="file"
    system_prompt: str = "You are a helpful assistant."
    tokenizer_name: str = "" # used when dataset="random"
    mode: str = "single-turn"           # "stress-test" | "single-turn" | "multi-turn"
    prefix_caching_required: bool = False  # True = server must be launched with --enable-prefix-caching
    min_turns: int = 1                   # multi-turn: minimum turns per session
    max_turns: int = 1                   # multi-turn: maximum turns per session
    num_sessions: int = 200              # multi-turn: number of concurrent sessions
    agent_type: str = ""           # "chat" | "coding" | "computer-use" | "customer-support"
    turn_style: str = "single-turn"  # "single-turn" | "multi-turn"
    serving_style: str = "not-disaggregated"  # "disaggregated" | "not-disaggregated"
    data_source: str = ""          # "sharegpt" | "swebench" | "file" | "random" | "test"


PROFILES: dict[str, WorkloadProfile] = {
    "chatbot-short": WorkloadProfile(
        name="chatbot-short",
        isl_tokens=2000,
        osl_tokens=500,
        isl_stddev=0.15,
        description="Simple Q&A, casual chat (max ISL/OSL filter bounds, ShareGPT natural distribution)",
        dataset="sharegpt",
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
    "chatbot-multi-turn": WorkloadProfile(
        name="chatbot-multi-turn",
        isl_tokens=4000,
        osl_tokens=1000,
        isl_stddev=0.15,
        description="Multi-turn conversation with history (max ISL/OSL filter bounds, ShareGPT natural distribution)",
        dataset="sharegpt",
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
    "rag-retrieval": WorkloadProfile(
        name="rag-retrieval",
        isl_tokens=6000,
        osl_tokens=1000,
        isl_stddev=0.15,
        description="RAG with 2-3 retrieved chunks (max ISL/OSL filter bounds, ShareGPT natural distribution)",
        dataset="sharegpt",
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
    "rag-heavy": WorkloadProfile(
        name="rag-heavy",
        isl_tokens=8192,
        osl_tokens=2000,
        isl_stddev=0.15,
        description="RAG with many chunks + system prompt (max ISL/OSL filter bounds, ShareGPT natural distribution)",
        dataset="sharegpt",
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
    "coding-assist": WorkloadProfile(
        name="coding-assist",
        isl_tokens=8192,
        osl_tokens=2048,
        isl_stddev=0.15,
        description="Code generation with context (max ISL/OSL filter bounds, ShareGPT natural distribution)",
        dataset="sharegpt",
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="coding",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
    "coding-heavy": WorkloadProfile(
        name="coding-heavy",
        isl_tokens=8192,
        osl_tokens=2048,
        isl_stddev=0.10,
        description="Large codebase context, multi-file generation (max ISL/OSL filter bounds, ShareGPT natural distribution)",
        dataset="sharegpt",
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="coding",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
    "summarization": WorkloadProfile(
        name="summarization",
        isl_tokens=8192,
        osl_tokens=1000,
        isl_stddev=0.15,
        description="Document summarization (max ISL/OSL filter bounds, ShareGPT natural distribution)",
        dataset="sharegpt",
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
    "agentic-tool-use": WorkloadProfile(
        name="agentic-tool-use",
        isl_tokens=4000,
        osl_tokens=1000,
        isl_stddev=0.15,
        description="Agent step with tool call output (max ISL/OSL filter bounds, ShareGPT natural distribution)",
        dataset="sharegpt",
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
    "coding-agent": WorkloadProfile(
        name="coding-agent",
        isl_tokens=17000,
        osl_tokens=800,
        isl_stddev=0.0,
        description="Real coding-agent prompts from Sequrity SWEBench runs (PLLM planning calls, ~17K ISL, ~800 OSL)",
        dataset="jsonl",
        file_path="data/coding_agent_prompts.jsonl",
        system_prompt="",  # system prompt is embedded in the JSONL
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="coding",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="swebench",
    ),
    # Legacy profiles from llm-bench (for direct comparison)
    "output-short": WorkloadProfile(
        name="output-short",
        isl_tokens=1200,
        osl_tokens=128,
        isl_stddev=0.0,
        description="llm-bench prefill-heavy: long input, short output",
        dataset="file",
        file_path="data/long_input_short_output.txt",
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="file",
    ),
    "output-long": WorkloadProfile(
        name="output-long",
        isl_tokens=180,
        osl_tokens=1024,
        isl_stddev=0.0,
        description="llm-bench decode-heavy: short input, long output",
        dataset="file",
        file_path="data/short_input_long_output.txt",
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="file",
    ),
    "test": WorkloadProfile(
        name="test",
        isl_tokens=10,
        osl_tokens=20,
        isl_stddev=0.0,
        description="Quick smoke test",
        dataset="test",
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="test",
    ),
    # InferenceX replication profile — for cross-validation only.
    # Uses the same random token generation algorithm as InferenceX
    # (SemiAnalysisAI/InferenceX utils/bench_serving/benchmark_serving.py).
    # NOT for production benchmarking: random tokens trigger EOS early,
    # giving unreliable output lengths (~50% of target on most models).
    # Use this to confirm inference-benchmark produces matching TTFT/TPOT/E2EL
    # vs InferenceX when given identical inputs.
    "random-inferencex": WorkloadProfile(
        name="random-inferencex",
        isl_tokens=1024,
        osl_tokens=1024,
        isl_stddev=0.0,
        description="InferenceX replication: random tokens ISL=1024 OSL=1024",
        dataset="random",
        tokenizer_name="meta-llama/Llama-3.1-8B-Instruct",
        mode="stress-test",
        prefix_caching_required=False,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="random",
    ),
    # Exact InferenceX replication using legacy numpy RNG (np.random.seed + np.random.randint).
    # If TTFT matches InferenceX (~144ms median), confirms TTFT gap is purely RNG/cache artifact.
    "random-inferencex-legacy": WorkloadProfile(
        name="random-inferencex-legacy",
        isl_tokens=1024,
        osl_tokens=1024,
        isl_stddev=0.0,
        description="InferenceX exact replication: legacy numpy RNG, same token formula",
        dataset="random-legacy",
        tokenizer_name="meta-llama/Llama-3.1-8B-Instruct",
        mode="stress-test",
        prefix_caching_required=False,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="random",
    ),
    # Same as random-inferencex but pre-applies chat template before sending,
    # replicating InferenceX's double-wrap bug (--backend openai-chat --use-chat-template).
    # Expected: higher TTFT than random-inferencex due to longer effective prefill.
    "random-inferencex-doublewrap": WorkloadProfile(
        name="random-inferencex-doublewrap",
        isl_tokens=1024,
        osl_tokens=1024,
        isl_stddev=0.0,
        description="InferenceX double-wrap bug replication (wrong example)",
        dataset="random-doublewrap",
        tokenizer_name="meta-llama/Llama-3.1-8B-Instruct",
        mode="stress-test",
        prefix_caching_required=False,
        agent_type="chat",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="random",
    ),
    # Multi-turn profiles — growing conversation history with prefix cache reuse
    "multi-turn-short": WorkloadProfile(
        name="multi-turn-short",
        isl_tokens=8192,
        osl_tokens=1000,
        isl_stddev=0.0,
        description="Short multi-turn: 3-5 turns, moderate growing context",
        dataset="sharegpt-multi-turn",
        mode="multi-turn",
        prefix_caching_required=True,
        min_turns=3,
        max_turns=5,
        num_sessions=200,
        agent_type="chat",
        turn_style="multi-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
    "multi-turn-long": WorkloadProfile(
        name="multi-turn-long",
        isl_tokens=16384,
        osl_tokens=1500,
        isl_stddev=0.0,
        description="Long multi-turn: 5-10 turns, large growing context for KV cache pressure",
        dataset="sharegpt-multi-turn",
        mode="multi-turn",
        prefix_caching_required=True,
        min_turns=5,
        max_turns=10,
        num_sessions=100,
        agent_type="chat",
        turn_style="multi-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
    "computer-use-basic": WorkloadProfile(
        name="computer-use-basic",
        isl_tokens=4000,
        osl_tokens=500,
        isl_stddev=0.15,
        description="Computer-use agent: screenshot analysis + action generation (placeholder)",
        dataset="sharegpt",  # placeholder until real dataset available
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="computer-use",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
    "customer-support-basic": WorkloadProfile(
        name="customer-support-basic",
        isl_tokens=3000,
        osl_tokens=800,
        isl_stddev=0.15,
        description="Customer support agent: ticket analysis + response (placeholder)",
        dataset="sharegpt",  # placeholder until real dataset available
        mode="single-turn",
        prefix_caching_required=True,
        agent_type="customer-support",
        turn_style="single-turn",
        serving_style="not-disaggregated",
        data_source="sharegpt",
    ),
}


def filter_profiles(
    agent_type: Optional[str] = None,
    turn_style: Optional[str] = None,
    serving_style: Optional[str] = None,
    data_source: Optional[str] = None,
    mode: Optional[str] = None,
) -> dict:
    """Filter profiles by tag values. None means 'any'."""
    result = {}
    for name, p in PROFILES.items():
        if agent_type is not None and p.agent_type != agent_type:
            continue
        if turn_style is not None and p.turn_style != turn_style:
            continue
        if serving_style is not None and p.serving_style != serving_style:
            continue
        if data_source is not None and p.data_source != data_source:
            continue
        if mode is not None and p.mode != mode:
            continue
        result[name] = p
    return result


# Convenience filters (backward compatible)
STRESS_TEST_PROFILES = filter_profiles(mode="stress-test")
SINGLE_TURN_PROFILES = filter_profiles(turn_style="single-turn")
MULTI_TURN_PROFILES = filter_profiles(turn_style="multi-turn")


def get_profile(name: str) -> WorkloadProfile:
    if name not in PROFILES:
        raise ValueError(f"Unknown profile '{name}'. Available: {list(PROFILES.keys())}")
    return PROFILES[name]
