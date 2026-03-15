"""
Workload profile definitions.

Based on real-world LLM usage patterns from OpenRouter 100T token study
and NVIDIA benchmarking guidance. Each profile defines typical ISL/OSL,
a description, and the data source to use.
"""

from dataclasses import dataclass


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
    ),
}


STRESS_TEST_PROFILES = {k: v for k, v in PROFILES.items() if v.mode == "stress-test"}
SINGLE_TURN_PROFILES = {k: v for k, v in PROFILES.items() if v.mode == "single-turn"}


def get_profile(name: str) -> WorkloadProfile:
    if name not in PROFILES:
        raise ValueError(f"Unknown profile '{name}'. Available: {list(PROFILES.keys())}")
    return PROFILES[name]
