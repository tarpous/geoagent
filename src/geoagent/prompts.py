"""Load versioned specialist system prompts from prompts/."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = ROOT / "prompts"

PROMPT_FILES = {
    "intake": "intake.md",
    "geodata": "geodata.md",
    "earth-obs": "earth_obs.md",
    "librarian": "librarian.md",
    "cartographer": "cartographer.md",
    "critic": "critic.md",
    "baseline": "baseline.md",
}


@lru_cache(maxsize=16)
def load_prompt(role: str) -> str:
    """Return the markdown system prompt for a specialist role."""
    filename = PROMPT_FILES.get(role)
    if filename is None:
        raise KeyError(f"unknown prompt role: {role}")
    path = PROMPTS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8").strip()


def available_prompts() -> list[str]:
    return sorted(PROMPT_FILES)
