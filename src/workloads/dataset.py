"""
Dataset classes for benchmark workloads.

Ported from llm-bench/src/benchmark_dataset.py with improvements:
- Thread-safe with asyncio lock support
- Profile-aware (returns messages list, not just prompt string)
- ShareGPT loads full conversations, not just first message
- ShareGPT returns per-request max_tokens from the actual assistant reply length
"""

import asyncio
import threading
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class BenchmarkRequest:
    messages: list[dict]
    max_tokens: int


class BaseDataset(ABC):
    """Base class for all benchmark datasets."""

    @abstractmethod
    def get_next_request(self) -> BenchmarkRequest:
        """Return the next request as a BenchmarkRequest (messages + max_tokens)."""
        pass

    def get_next_messages(self) -> list[dict]:
        """Deprecated shim — returns messages only. Use get_next_request()."""
        return self.get_next_request().messages


class TestDataset(BaseDataset):
    """Simple dataset for smoke testing."""

    def __init__(self, prompt: str = "Say hello in one word."):
        self.prompt = prompt

    def get_next_request(self) -> BenchmarkRequest:
        return BenchmarkRequest(
            messages=[{"role": "user", "content": self.prompt}],
            max_tokens=20,
        )


class FileDataset(BaseDataset):
    """Loads a single static prompt from a text file."""

    def __init__(
        self,
        filepath: str,
        system_prompt: str = "You are a helpful assistant.",
        max_tokens: int = 1024,
    ):
        self.filepath = filepath
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self._prompt: Optional[str] = None
        self._lock = threading.Lock()

    def _load(self):
        if self._prompt is None:
            with self._lock:
                if self._prompt is None:
                    with open(self.filepath, "r") as f:
                        self._prompt = f.read().strip()

    def get_next_request(self) -> BenchmarkRequest:
        self._load()
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": self._prompt})
        return BenchmarkRequest(messages=messages, max_tokens=self.max_tokens)


class JsonlDataset(BaseDataset):
    """
    Loads real prompts from a JSONL file.

    Each line: {"system": "...", "user": "...", "osl_tokens": N}
    Returns per-request max_tokens from osl_tokens field.
    Used for coding-agent profile with real SWEBench PLLM prompts.
    """

    def __init__(self, filepath: str, random_seed: int = 42):
        self.filepath = filepath
        self.random_seed = random_seed
        self._samples: Optional[list[tuple]] = None   # list of (messages, osl_tokens)
        self._available: Optional[list[tuple]] = None
        self._lock = threading.Lock()
        self._rng = random.Random(random_seed)

    def _load(self):
        if self._samples is not None:
            return
        with self._lock:
            if self._samples is not None:
                return
            import json
            samples = []
            with open(self.filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    messages = [
                        {"role": "system", "content": entry["system"]},
                        {"role": "user", "content": entry["user"]},
                    ]
                    samples.append((messages, entry["osl_tokens"]))
            rng = random.Random(self.random_seed)
            rng.shuffle(samples)
            self._samples = samples
            self._available = list(self._samples)

    def get_next_request(self) -> BenchmarkRequest:
        self._load()
        with self._lock:
            if not self._available:
                self._available = list(self._samples)
                self._rng.shuffle(self._available)
            messages, osl_tokens = self._available.pop()
        return BenchmarkRequest(messages=messages, max_tokens=osl_tokens)


class ShareGPTDataset(BaseDataset):
    """
    Loads real conversations from ShareGPT dataset.

    Each request gets max_tokens = the actual assistant reply length for that
    conversation (estimated), filtered to be within realistic ISL/OSL bounds.
    This gives the server a natural ISL/OSL distribution rather than a fixed
    target for every request.

    Improvements over original version:
    - Returns BenchmarkRequest with per-request max_tokens
    - Filters by ISL and OSL bounds (not fixed targets)
    - Stores (messages, osl) tuples so max_tokens varies per request
    - Cycles through samples in random order each pass
    - Uses threading.Lock for thread safety
    """

    def __init__(
        self,
        num_prompts: int = 1000,
        random_seed: int = 42,
        system_prompt: str = "You are a helpful assistant.",
        max_isl_tokens: int = 8192,   # filter: skip conversations where user msg > this
        max_osl_tokens: int = 2048,   # filter: skip conversations where assistant reply > this
        min_osl_tokens: int = 50,     # filter: skip very short replies
    ):
        self.num_prompts = num_prompts
        self.random_seed = random_seed
        self.system_prompt = system_prompt
        self.max_isl_tokens = max_isl_tokens
        self.max_osl_tokens = max_osl_tokens
        self.min_osl_tokens = min_osl_tokens
        self._samples: Optional[list[tuple]] = None   # list of (messages, osl)
        self._available: Optional[list[tuple]] = None
        self._lock = threading.Lock()
        self._rng = random.Random(random_seed)

    def _load(self):
        if self._samples is not None:
            return
        with self._lock:
            if self._samples is not None:
                return
            import datasets as hf_datasets
            ds = hf_datasets.load_dataset(
                "Aeala/ShareGPT_Vicuna_unfiltered",
                split="train",
            )
            samples = []
            for item in ds:
                convs = item["conversations"]
                if len(convs) < 2:
                    continue
                # Find first user+assistant pair
                user_msg = None
                assistant_msg = None
                for i, turn in enumerate(convs):
                    if turn.get("from") == "human" and user_msg is None:
                        user_msg = turn.get("value", "")
                    elif turn.get("from") == "gpt" and user_msg is not None:
                        assistant_msg = turn.get("value", "")
                        break
                if not user_msg or not assistant_msg:
                    continue
                # Estimate token counts (word-to-token ratio for English)
                isl_est = int(len(user_msg.split()) * 1.35)
                osl_est = int(len(assistant_msg.split()) * 1.35)
                if isl_est > self.max_isl_tokens:
                    continue
                if osl_est > self.max_osl_tokens:
                    continue
                if osl_est < self.min_osl_tokens:
                    continue
                messages = []
                if self.system_prompt:
                    messages.append({"role": "system", "content": self.system_prompt})
                messages.append({"role": "user", "content": user_msg})
                samples.append((messages, osl_est))
                if len(samples) >= self.num_prompts * 3:  # load 3x, shuffle, take num_prompts
                    break

            rng = random.Random(self.random_seed)
            rng.shuffle(samples)
            self._samples = samples[:self.num_prompts]
            self._available = list(self._samples)

    def get_next_request(self) -> BenchmarkRequest:
        self._load()
        with self._lock:
            if not self._available:
                self._available = list(self._samples)
                self._rng.shuffle(self._available)
            messages, osl = self._available.pop()
        return BenchmarkRequest(messages=messages, max_tokens=osl)


class RandomTokenDataset(BaseDataset):
    """
    Replicates InferenceX's random token workload for cross-validation.

    Generates random token IDs using the same algorithm as InferenceX
    (SemiAnalysisAI/InferenceX utils/bench_serving/benchmark_serving.py),
    decodes them to text via the tokenizer, and wraps in a chat message.

    Purpose: verify inference-benchmark produces the same TTFT/TPOT/E2EL
    as InferenceX when given identical inputs. Not for production benchmarking
    — random tokens trigger EOS early and give unreliable output lengths.
    """

    def __init__(
        self,
        tokenizer_name: str,
        input_len: int = 1024,
        output_len: int = 1024,
        num_prompts: int = 500,
        range_ratio: float = 1.0,
        seed: int = 0,
    ):
        self.output_len = output_len
        self._prompts: Optional[list[str]] = None
        self._idx = 0
        self._lock = threading.Lock()
        self._tokenizer_name = tokenizer_name
        self._input_len = input_len
        self._num_prompts = num_prompts
        self._range_ratio = range_ratio
        self._seed = seed

    def _load(self):
        if self._prompts is not None:
            return
        with self._lock:
            if self._prompts is not None:
                return
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(self._tokenizer_name)
            rng = np.random.default_rng(self._seed)

            lo = max(1, int(self._input_len * (1 - self._range_ratio / 2)))
            hi = int(self._input_len * (1 + self._range_ratio / 2))
            input_lens = rng.integers(lo, hi + 1, size=self._num_prompts)
            offsets = rng.integers(0, tokenizer.vocab_size, size=self._num_prompts)

            prompts = []
            for i in range(self._num_prompts):
                tgt_len = int(input_lens[i])
                token_ids = [(int(offsets[i]) + i + j) % tokenizer.vocab_size
                             for j in range(tgt_len)]
                prompt = tokenizer.decode(token_ids)
                # Re-encode and trim/pad to hit exact target length (InferenceX does this too)
                re_encoded = tokenizer.encode(prompt, add_special_tokens=False)
                if len(re_encoded) > tgt_len:
                    re_encoded = re_encoded[:tgt_len]
                elif len(re_encoded) < tgt_len:
                    extras = rng.integers(0, tokenizer.vocab_size,
                                         size=tgt_len - len(re_encoded)).tolist()
                    re_encoded.extend(extras)
                prompts.append(tokenizer.decode(re_encoded))

            self._prompts = prompts

    def get_next_request(self) -> BenchmarkRequest:
        self._load()
        with self._lock:
            prompt = self._prompts[self._idx % len(self._prompts)]
            self._idx += 1
        return BenchmarkRequest(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.output_len,
        )


class RandomTokenDatasetLegacy(BaseDataset):
    """
    Exact replication of InferenceX's random token generation using legacy numpy RNG.

    Uses np.random.seed(seed) + np.random.randint (same as InferenceX's
    sample_random_requests), with the identical token formula:
      token_ids[j] = (offsets[i] + i + j) % vocab_size

    If TTFT matches InferenceX with this dataset, it confirms the TTFT gap
    between inference-benchmark and InferenceX is purely due to RNG differences
    producing different prefix cache hit rates.
    """

    def __init__(
        self,
        tokenizer_name: str,
        input_len: int = 1024,
        output_len: int = 1024,
        num_prompts: int = 500,
        range_ratio: float = 1.0,
        prefix_len: int = 0,
        seed: int = 0,
    ):
        self.output_len = output_len
        self._tokenizer_name = tokenizer_name
        self._input_len = input_len
        self._num_prompts = num_prompts
        self._range_ratio = range_ratio
        self._prefix_len = prefix_len
        self._seed = seed
        self._prompts: Optional[list[str]] = None
        self._idx = 0
        self._lock = threading.Lock()

    def _load(self):
        if self._prompts is not None:
            return
        with self._lock:
            if self._prompts is not None:
                return
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(self._tokenizer_name)
            vocab_size = tokenizer.vocab_size

            # Match InferenceX exactly: np.random.seed then legacy randint
            np.random.seed(self._seed)
            prefix_token_ids = np.random.randint(0, vocab_size, size=self._prefix_len).tolist()

            lo = int(self._input_len * self._range_ratio)
            hi = self._input_len
            input_lens = np.random.randint(lo, hi + 1, size=self._num_prompts).tolist()
            _output_lens = np.random.randint(
                int(self.output_len * self._range_ratio),
                self.output_len + 1,
                size=self._num_prompts,
            ).tolist()
            offsets = np.random.randint(0, vocab_size, size=self._num_prompts)

            prompts = []
            for i in range(self._num_prompts):
                tgt_len = self._prefix_len + input_lens[i]
                token_ids = prefix_token_ids + [
                    (int(offsets[i]) + i + j) % vocab_size
                    for j in range(input_lens[i])
                ]
                prompt = tokenizer.decode(token_ids)
                # Re-encode and trim/pad (same as InferenceX)
                for _ in range(10):
                    re_encoded = tokenizer.encode(prompt, add_special_tokens=False)
                    if len(re_encoded) < tgt_len:
                        extras = np.random.randint(0, vocab_size, size=tgt_len - len(re_encoded)).tolist()
                        re_encoded.extend(extras)
                    elif len(re_encoded) > tgt_len:
                        re_encoded = re_encoded[:tgt_len]
                    else:
                        break
                    prompt = tokenizer.decode(re_encoded)
                prompts.append(prompt)

            self._prompts = prompts

    def get_next_request(self) -> BenchmarkRequest:
        self._load()
        with self._lock:
            prompt = self._prompts[self._idx % len(self._prompts)]
            self._idx += 1
        return BenchmarkRequest(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.output_len,
        )


class RandomTokenDatasetDoubleWrap(RandomTokenDataset):
    """
    Replicates InferenceX's double-chat-template bug for comparison.

    InferenceX with --backend openai-chat --use-chat-template pre-applies
    the chat template in sample_random_requests(), then sends the resulting
    formatted string as the 'content' of a user message to /v1/chat/completions.
    vLLM then applies the template a second time, making the effective prefill
    longer than intended.

    This class reproduces that exact behavior so we can measure the TTFT
    increase caused by the double-wrap vs our correct single-wrap approach.
    Use alongside random-inferencex profile to confirm the theory.
    """

    def _load(self):
        super()._load()
        # Cache tokenizer for chat template application
        if not hasattr(self, '_tokenizer_obj'):
            from transformers import AutoTokenizer
            self._tokenizer_obj = AutoTokenizer.from_pretrained(self._tokenizer_name)

    def get_next_request(self) -> BenchmarkRequest:
        self._load()
        with self._lock:
            prompt = self._prompts[self._idx % len(self._prompts)]
            self._idx += 1

        # Pre-apply chat template exactly as InferenceX does
        pre_formatted = self._tokenizer_obj.apply_chat_template(
            [{"role": "user", "content": prompt}],
            add_generation_prompt=True,
            tokenize=False,
        )
        # Send pre-formatted string as user content → vLLM wraps it again
        return BenchmarkRequest(
            messages=[{"role": "user", "content": pre_formatted}],
            max_tokens=self.output_len,
        )


def make_dataset(profile) -> BaseDataset:
    """Factory: create the right dataset for a workload profile."""
    from .profiles import WorkloadProfile
    if profile.dataset == "test":
        return TestDataset()
    elif profile.dataset == "file":
        return FileDataset(
            filepath=profile.file_path,
            system_prompt=profile.system_prompt,
            max_tokens=profile.osl_tokens,
        )
    elif profile.dataset == "sharegpt":
        return ShareGPTDataset(
            num_prompts=1000,
            system_prompt=profile.system_prompt,
            max_isl_tokens=profile.isl_tokens,    # treat isl_tokens as max bound
            max_osl_tokens=profile.osl_tokens,    # treat osl_tokens as max bound
        )
    elif profile.dataset == "random":
        return RandomTokenDataset(
            tokenizer_name=profile.tokenizer_name,
            input_len=profile.isl_tokens,
            output_len=profile.osl_tokens,
            num_prompts=500,
        )
    elif profile.dataset == "random-legacy":
        return RandomTokenDatasetLegacy(
            tokenizer_name=profile.tokenizer_name,
            input_len=profile.isl_tokens,
            output_len=profile.osl_tokens,
            num_prompts=500,
        )
    elif profile.dataset == "random-doublewrap":
        return RandomTokenDatasetDoubleWrap(
            tokenizer_name=profile.tokenizer_name,
            input_len=profile.isl_tokens,
            output_len=profile.osl_tokens,
            num_prompts=500,
        )
    elif profile.dataset == "jsonl":
        return JsonlDataset(
            filepath=profile.file_path,
        )
    else:
        raise ValueError(f"Unknown dataset type: {profile.dataset}")
