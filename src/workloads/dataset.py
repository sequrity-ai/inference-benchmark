"""
Dataset classes for benchmark workloads.

Ported from llm-bench/src/benchmark_dataset.py with improvements:
- Thread-safe with asyncio lock support
- Profile-aware (returns messages list, not just prompt string)
- ShareGPT loads full conversations, not just first message
"""

import asyncio
import threading
import random
from abc import ABC, abstractmethod
from typing import Optional


class BaseDataset(ABC):
    """Base class for all benchmark datasets."""

    @abstractmethod
    def get_next_messages(self) -> list[dict]:
        """Return the next request as an OpenAI messages list."""
        pass


class TestDataset(BaseDataset):
    """Simple dataset for smoke testing."""

    def __init__(self, prompt: str = "Say hello in one word."):
        self.prompt = prompt

    def get_next_messages(self) -> list[dict]:
        return [{"role": "user", "content": self.prompt}]


class FileDataset(BaseDataset):
    """Loads a single static prompt from a text file."""

    def __init__(self, filepath: str, system_prompt: str = "You are a helpful assistant."):
        self.filepath = filepath
        self.system_prompt = system_prompt
        self._prompt: Optional[str] = None
        self._lock = threading.Lock()

    def _load(self):
        if self._prompt is None:
            with self._lock:
                if self._prompt is None:
                    with open(self.filepath, "r") as f:
                        self._prompt = f.read().strip()

    def get_next_messages(self) -> list[dict]:
        self._load()
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": self._prompt})
        return messages


class ShareGPTDataset(BaseDataset):
    """
    Loads real conversations from ShareGPT dataset.

    Improvements over llm-bench version:
    - Returns full messages list (system + user), not just user string
    - Cycles through prompts in random order each pass
    - Uses threading.Lock for thread safety
    """

    def __init__(
        self,
        num_prompts: int = 500,
        random_seed: int = 42,
        system_prompt: str = "You are a helpful assistant.",
    ):
        self.num_prompts = num_prompts
        self.random_seed = random_seed
        self.system_prompt = system_prompt
        self._prompts: Optional[list[str]] = None
        self._available: Optional[list[str]] = None
        self._lock = threading.Lock()
        self._rng = random.Random(random_seed)

    def _load(self):
        if self._prompts is None:
            with self._lock:
                if self._prompts is None:
                    import datasets as hf_datasets
                    ds = hf_datasets.load_dataset(
                        "Aeala/ShareGPT_Vicuna_unfiltered",
                        split="train",
                    )
                    ds = ds.shuffle(seed=self.random_seed).select(range(self.num_prompts))
                    self._prompts = [
                        conv[0]["value"]
                        for conv in ds["conversations"]
                        if conv and len(conv) > 0
                    ]
                    self._available = list(self._prompts)

    def get_next_messages(self) -> list[dict]:
        self._load()
        with self._lock:
            if not self._available:
                self._available = list(self._prompts)
                self._rng.shuffle(self._available)
            prompt = self._available.pop()

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages


def make_dataset(profile) -> BaseDataset:
    """Factory: create the right dataset for a workload profile."""
    from .profiles import WorkloadProfile
    if profile.dataset == "test":
        return TestDataset()
    elif profile.dataset == "file":
        return FileDataset(
            filepath=profile.file_path,
            system_prompt=profile.system_prompt,
        )
    elif profile.dataset == "sharegpt":
        return ShareGPTDataset(
            num_prompts=500,
            system_prompt=profile.system_prompt,
        )
    else:
        raise ValueError(f"Unknown dataset type: {profile.dataset}")
