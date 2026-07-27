# Local LLM launch glue

Scripts expect **host GPU** servers (not CPU-only containers by default).

| Backend | Scripts | Default URL |
|---|---|---|
| llama.cpp (default demo) | `llamacpp/run-server.sh`, `llamacpp/run-server.ps1` | `http://127.0.0.1:8080/v1` |
| vLLM (serving / ablation) | `vllm/run-server.sh`, `vllm/run-server.ps1` | `http://127.0.0.1:8000/v1` |

Weights are downloaded with the Hugging Face CLI into `models/` (gitignored binaries).
Compose services should reach these servers via `host.docker.internal`.
