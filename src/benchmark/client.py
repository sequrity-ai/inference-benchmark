"""
Async streaming benchmark client.

Uses aiohttp with SSE streaming to measure:
- TTFT: time from request sent to first token received (parsed from SSE data: lines)
- ITL: inter-token latencies (list of times between consecutive tokens)
- E2EL: total request time
- Token counts from usage field in final SSE message
"""

import asyncio
import time
import json
from dataclasses import dataclass, field
from typing import Optional
import aiohttp


@dataclass
class RequestResult:
    """Per-request benchmark result."""
    success: bool
    ttft: Optional[float] = None          # seconds to first token
    itl: list[float] = field(default_factory=list)  # inter-token latencies (seconds)
    e2el: Optional[float] = None          # end-to-end latency (seconds)
    input_tokens: int = 0
    output_tokens: int = 0
    error: Optional[str] = None
    prompt_tokens_from_usage: int = 0
    completion_tokens_from_usage: int = 0

    @property
    def tpot(self) -> Optional[float]:
        """Time per output token (mean ITL), excluding first token."""
        if not self.itl:
            return None
        return sum(self.itl) / len(self.itl)


async def send_chat_request(
    session: aiohttp.ClientSession,
    url: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float = 1.0,
    api_key: str = "test",
    extra_headers: Optional[dict] = None,
) -> RequestResult:
    """
    Send a single streaming chat completion request and record metrics.

    Parses SSE stream properly: each `data: {...}` line is one token event.
    First data line arrival = TTFT. Time between consecutive data lines = ITL.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    start_time = time.perf_counter()
    ttft = None
    itl = []
    last_token_time = None
    input_tokens = 0
    output_tokens = 0
    error = None

    try:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                return RequestResult(
                    success=False,
                    e2el=time.perf_counter() - start_time,
                    error=f"HTTP {resp.status}: {body[:200]}",
                )

            # Parse SSE stream line by line
            async for raw_line in resp.content:
                line = raw_line.decode("utf-8").strip()

                if not line.startswith("data:"):
                    continue

                data_str = line[len("data:"):].strip()

                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                now = time.perf_counter()

                # Extract usage from final chunk (stream_options: include_usage)
                if chunk.get("usage"):
                    usage = chunk["usage"]
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)

                # Check if this chunk has a token
                choices = chunk.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                content = delta.get("content")

                if content is None:
                    # Could be role message or finish_reason chunk — not a token
                    continue

                # This is a real token
                if ttft is None:
                    ttft = now - start_time
                    last_token_time = now
                else:
                    itl.append(now - last_token_time)
                    last_token_time = now

        e2el = time.perf_counter() - start_time
        return RequestResult(
            success=True,
            ttft=ttft,
            itl=itl,
            e2el=e2el,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    except asyncio.CancelledError:
        raise
    except Exception as e:
        return RequestResult(
            success=False,
            e2el=time.perf_counter() - start_time,
            error=str(e),
        )


async def run_warmup(
    url: str,
    model: str,
    api_key: str,
    num_requests: int = 3,
    timeout: int = 60,
) -> None:
    """Send warmup requests and discard results."""
    warmup_messages = [{"role": "user", "content": "Hello"}]
    connector = aiohttp.TCPConnector(limit=num_requests)
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=timeout),
    ) as session:
        tasks = [
            send_chat_request(session, url, model, warmup_messages, max_tokens=10, api_key=api_key)
            for _ in range(num_requests)
        ]
        await asyncio.gather(*tasks)
