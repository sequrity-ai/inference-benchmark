"""
Multi-turn mode — growing conversation history with prefix caching.

NOT YET IMPLEMENTED. Stub only.

Planned design:
  - ConversationSession: maintains per-user history across turns
  - Interleaved round-robin scheduling: [A1,B1,C1,A2,B2,C2,...] forces KV
    cache eviction between turns, testing offloading under memory pressure
  - Server: prefix caching ON (same as single-turn)
  - Client: growing message list per session (no truncation — engine handles it)

Server requirements (same as single-turn):
  - vLLM: --enable-prefix-caching
  - SGLang: radix cache ON by default
"""

REQUIRED_CLIENT_FLAGS: list[str] = []
PREFIX_CACHING_REQUIRED = True
PROFILES: list[str] = []  # no profiles yet

SERVER_NOTES = """
Not implemented. See src/modes/multi_turn.py for planned design.
"""
