"""
Stress-test mode — mirrors InferenceX methodology.

Server requirements:
  - Prefix caching: OFF (vLLM: omit --enable-prefix-caching)
  - SGLang: --disable-radix-cache

Client requirements:
  - --ignore-eos: REQUIRED for FP8 models (without it, OSL hit rate ~37-51%)
  - For bfloat16 models, --ignore-eos is still recommended for correctness

Profiles: random-inferencex, random-inferencex-legacy
"""

REQUIRED_CLIENT_FLAGS = ["--ignore-eos"]
PREFIX_CACHING_REQUIRED = False

PROFILES = ["random-inferencex", "random-inferencex-legacy"]

SERVER_NOTES = """
vLLM: do NOT pass --enable-prefix-caching
SGLang: pass --disable-radix-cache
"""
