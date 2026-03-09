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
    isl_tokens: int          # target input sequence length
    osl_tokens: int          # target output sequence length (max_tokens)
    isl_stddev: float        # stddev as fraction of isl (for Gaussian sampling)
    description: str
    dataset: str             # "sharegpt", "file", "test"
    file_path: str = ""      # used when dataset="file"
    system_prompt: str = "You are a helpful assistant."


PROFILES: dict[str, WorkloadProfile] = {
    "chatbot-short": WorkloadProfile(
        name="chatbot-short",
        isl_tokens=200,
        osl_tokens=150,
        isl_stddev=0.15,
        description="Simple Q&A, casual chat",
        dataset="sharegpt",
    ),
    "chatbot-multi-turn": WorkloadProfile(
        name="chatbot-multi-turn",
        isl_tokens=1500,
        osl_tokens=300,
        isl_stddev=0.15,
        description="Multi-turn conversation with history",
        dataset="sharegpt",
    ),
    "rag-retrieval": WorkloadProfile(
        name="rag-retrieval",
        isl_tokens=3000,
        osl_tokens=500,
        isl_stddev=0.15,
        description="RAG with 2-3 retrieved chunks",
        dataset="sharegpt",
    ),
    "rag-heavy": WorkloadProfile(
        name="rag-heavy",
        isl_tokens=6000,
        osl_tokens=800,
        isl_stddev=0.15,
        description="RAG with many chunks + system prompt",
        dataset="sharegpt",
    ),
    "coding-assist": WorkloadProfile(
        name="coding-assist",
        isl_tokens=4000,
        osl_tokens=1500,
        isl_stddev=0.15,
        description="Code generation with context",
        dataset="sharegpt",
    ),
    "coding-heavy": WorkloadProfile(
        name="coding-heavy",
        isl_tokens=12000,
        osl_tokens=3000,
        isl_stddev=0.10,
        description="Large codebase context, multi-file generation",
        dataset="sharegpt",
    ),
    "summarization": WorkloadProfile(
        name="summarization",
        isl_tokens=8000,
        osl_tokens=400,
        isl_stddev=0.15,
        description="Document summarization",
        dataset="sharegpt",
    ),
    "agentic-tool-use": WorkloadProfile(
        name="agentic-tool-use",
        isl_tokens=2000,
        osl_tokens=200,
        isl_stddev=0.15,
        description="Agent step with tool call output",
        dataset="sharegpt",
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
    ),
    "output-long": WorkloadProfile(
        name="output-long",
        isl_tokens=180,
        osl_tokens=1024,
        isl_stddev=0.0,
        description="llm-bench decode-heavy: short input, long output",
        dataset="file",
        file_path="data/short_input_long_output.txt",
    ),
    "test": WorkloadProfile(
        name="test",
        isl_tokens=10,
        osl_tokens=20,
        isl_stddev=0.0,
        description="Quick smoke test",
        dataset="test",
    ),
}


def get_profile(name: str) -> WorkloadProfile:
    if name not in PROFILES:
        raise ValueError(f"Unknown profile '{name}'. Available: {list(PROFILES.keys())}")
    return PROFILES[name]
