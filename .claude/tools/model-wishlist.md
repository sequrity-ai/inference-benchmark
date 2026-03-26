# Model Wishlist — Requires More GPUs

Models the lab wants to benchmark but don't fit on 2x H100 at original precision.

## Blocked by VRAM

| Model | Total Params | Active | BF16 Size | Min GPUs (BF16) | HF Repo |
|-------|:-----------:|:------:|:---------:|:---------------:|---------|
| MiniMax-M2.5 | 230B | 10B | ~460GB | 6x H100 | `MiniMaxAI/MiniMax-M2.5` |
| MiniMax-M2.1 | 230B | 10B | ~460GB | 6x H100 | `MiniMaxAI/MiniMax-M2.1` |
| DeepSeek-V3.2 | 671B | 37B | ~1.3TB | 8-10x H100 | `deepseek-ai/DeepSeek-V3.2` |
| GLM-4.6 | 355B | 32B | ~710GB | 5x H100 | (Zhipu/Z.ai) |
| GLM-5 | 744B | 40B | ~1.5TB | 10x H100 | `zai-org/GLM-5` |

## FP8 Feasibility (halves weight memory)

| Model | FP8 Size | Min GPUs (FP8) |
|-------|:--------:|:--------------:|
| MiniMax-M2.5 | ~230GB | 3x H100 |
| DeepSeek-V3.2 | ~670GB | 5x H100 |
| GLM-4.6 | ~355GB | 5x H100 |
| GLM-5 | ~750GB | 5-6x H100 |

## Notes
- All are MoE architectures — total params >> active params, but ALL expert weights must be in VRAM
- MiniMax has no small/dense models — smallest is 230B MoE
- DeepSeek-V3.2 has variants: base, Speciale, Exp
- GLM-5 trained on Huawei Ascend chips, may need compatibility testing
- Consider RunPod 8xH100 pod for these models
