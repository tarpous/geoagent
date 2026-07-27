#!/usr/bin/env bash
# Launch vLLM OpenAI-compatible server for the serving / ablation profile.
set -euo pipefail

MODEL_ID="${MODEL_ID:-Qwen/Qwen3.5-9B}"
HOST="${VLLM_HOST:-127.0.0.1}"
PORT="${VLLM_PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-16384}"
QUANTIZATION="${QUANTIZATION:-awq}"

if ! command -v vllm >/dev/null 2>&1; then
  echo "vllm not found on PATH. Install/run vLLM in an approved container or env first." >&2
  exit 1
fi

exec vllm serve "$MODEL_ID" \
  --host "$HOST" \
  --port "$PORT" \
  --max-model-len "$MAX_MODEL_LEN" \
  --quantization "$QUANTIZATION"
