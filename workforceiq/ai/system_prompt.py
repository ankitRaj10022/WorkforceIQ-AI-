from __future__ import annotations

from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "workforceiq_master_system_prompt.md"


def load_master_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_runtime_system_prompt(*, role: str | None = None, scope: str | None = None) -> str:
    prompt = load_master_system_prompt().strip()
    runtime_lines = [
        "",
        "## RUNTIME CONTEXT",
        f"- Active role: {role or 'UNKNOWN'}",
        f"- Active scope: {scope or 'UNSPECIFIED'}",
        "- Timestamps must be emitted in ISO 8601 UTC.",
        "- Do not exceed 500 records in a single response.",
    ]
    return "\n".join([prompt, *runtime_lines])
