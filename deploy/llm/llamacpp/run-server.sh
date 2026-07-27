#!/usr/bin/env bash
# Launch llama-server against a local GGUF on the host GPU.
# Weights are not committed; download with the Hugging Face CLI into models/llm/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
MODEL_PATH="${MODEL_PATH:-$ROOT/models/llm/demo.gguf}"
HOST="${LLAMA_HOST:-127.0.0.1}"
PORT="${LLAMA_PORT:-8080}"
N_CTX="${N_CTX:-16384}"
N_GPU_LAYERS="${N_GPU_LAYERS:-99}"

if [[ ! -f "$MODEL_PATH" ]]; then
  echo "Missing GGUF at $MODEL_PATH" >&2
  echo "Set MODEL_PATH or place the demo GGUF under models/llm/." >&2
  exit 1
fi

if ! command -v llama-server >/dev/null 2>&1; then
  echo "llama-server not found on PATH. Build/install llama.cpp CUDA binaries first." >&2
  exit 1
fi

exec llama-server \
  --model "$MODEL_PATH" \
  --host "$HOST" \
  --port "$PORT" \
  --ctx-size "$N_CTX" \
  --n-gpu-layers "$N_GPU_LAYERS" \
  --jinja
