"""Model selection and provider-specific options for the daily generators."""
from __future__ import annotations

import os


DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


def llm_settings(*, allow_desirecore: bool = False) -> tuple[str | None, str, str]:
    if allow_desirecore and os.environ.get("DESIRECORE_CLOUD_API_KEY"):
        return (
            os.environ["DESIRECORE_CLOUD_API_KEY"],
            os.environ.get("DESIRECORE_BASE_URL", "").rstrip("/"),
            os.environ.get("DESIRECORE_MODEL", ""),
        )
    if os.environ.get("DEEPSEEK_API_KEY"):
        return (
            os.environ["DEEPSEEK_API_KEY"],
            DEEPSEEK_BASE_URL,
            os.environ.get("DEEPSEEK_MODEL", "").strip() or "deepseek-flash",
        )
    return os.environ.get("OPENAI_API_KEY"), "https://api.openai.com/v1", "gpt-4o"


def completion_options(base_url: str) -> dict:
    # DeepSeek now enables thinking by default. Keep the existing final-text
    # token budgets and timeouts; never send this extension to other providers.
    if base_url.rstrip("/") == DEEPSEEK_BASE_URL:
        return {"thinking": {"type": "disabled"}}
    return {}
