"""OpenAI-compatible client for llama.cpp / vLLM backends."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx
import yaml

BackendName = Literal["llamacpp", "vllm"]


@dataclass(slots=True)
class LLMConfig:
    backend: BackendName
    base_url: str
    model: str
    temperature: float = 0.1
    top_p: float = 0.9
    seed: int | None = 42
    timeout_s: float = 120.0


def load_role_config(
    role: str,
    *,
    profile: str | None = None,
    config_path: Path | None = None,
) -> LLMConfig:
    path = config_path or Path(__file__).resolve().parents[3] / "configs" / "models.yaml"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    profile_name = profile or data.get("default_profile", "demo")
    profile_data = data["profiles"][profile_name]
    backend: BackendName = profile_data.get("backend", "llamacpp")
    role_cfg = profile_data["roles"][role]
    backend_urls = data.get("backends", {})
    base_url = os.environ.get("LLM_BASE_URL") or backend_urls.get(backend, {}).get(
        "base_url", "http://127.0.0.1:8080/v1"
    )
    env_backend = os.environ.get("LLM_BACKEND")
    if env_backend in ("llamacpp", "vllm"):
        backend = env_backend  # type: ignore[assignment]
        base_url = os.environ.get("LLM_BASE_URL") or backend_urls.get(backend, {}).get(
            "base_url", base_url
        )

    quant = role_cfg.get("quant", "")
    model_id = f"{role_cfg['model']}@{quant}" if quant else role_cfg["model"]
    return LLMConfig(
        backend=backend,
        base_url=base_url.rstrip("/"),
        model=model_id,
        temperature=float(role_cfg.get("temperature", 0.1)),
        top_p=float(role_cfg.get("top_p", 0.9)),
        seed=profile_data.get("seed"),
    )


class LocalChatClient:
    """Thin OpenAI-compatible chat client. No cloud vendor SDKs."""

    def __init__(self, config: LLMConfig, *, client: httpx.Client | None = None) -> None:
        self.config = config
        self._client = client or httpx.Client(base_url=config.base_url, timeout=config.timeout_s)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> LocalChatClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature if temperature is None else temperature,
            "top_p": self.config.top_p,
        }
        if self.config.seed is not None:
            body["seed"] = self.config.seed
        if response_format is not None:
            body["response_format"] = response_format

        response = self._client.post("/chat/completions", json=body)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
