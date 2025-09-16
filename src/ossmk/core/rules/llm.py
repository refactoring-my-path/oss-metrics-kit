from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast


@dataclass
class LLMConfig:
    provider: str  # 'openai' | 'anthropic' | 'azure-openai'
    model: str
    api_key: str | None = None
    endpoint: str | None = None  # for Azure


SYSTEM_PROMPT = (
    "You are a helpful assistant that designs fair scoring rules for OSS contributions. "
    "Return a minimal TOML with [dimensions.<name>] having 'kinds', 'weight', and "
    "optional 'weights_by_kind'. Also add [fairness.clip_per_user_day] with daily caps per kind."
)


def _openai_complete(cfg: LLMConfig, content: str) -> str:
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "OpenAI client not installed. pip install 'oss-metrics-kit[llm-openai]'"
        ) from e
    client: Any = cast(Any, OpenAI(api_key=cfg.api_key))
    resp: Any = client.chat.completions.create(
        model=cfg.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        temperature=0.2,
    )
    return cast(str, resp.choices[0].message.content or "")


def _anthropic_complete(cfg: LLMConfig, content: str) -> str:
    try:
        import anthropic  # type: ignore[reportMissingImports]
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Anthropic client not installed. pip install 'oss-metrics-kit[llm-anthropic]'"
        ) from e
    anthropic_mod: Any = anthropic
    client: Any = anthropic_mod.Anthropic(api_key=cfg.api_key)
    msg: Any = client.messages.create(
        model=cfg.model,
        max_tokens=1000,
        temperature=0.2,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    # anthropic returns list of content blocks; avoid unknown member types
    parts: list[str] = []
    for block in msg.content:
        parts.append(str(getattr(block, "text", "")))
    return "".join(parts)


def suggest_rules_from_events(events: list[dict[str, Any]], cfg: LLMConfig) -> str:
    """Return TOML text suggested by the chosen LLM provider.

    The caller is responsible for parsing and validating the TOML into a RuleSet if desired.
    """
    # Compress to counts per kind to avoid leaking full data and reduce tokens
    counts: dict[str, int] = {}
    for e in events:
        k = str(e.get("kind"))
        counts[k] = counts.get(k, 0) + 1
    prefix = (
        "Please propose fair scoring rules for the following event counts as TOML.\n"
    )
    content = prefix + json.dumps({"counts": counts}, ensure_ascii=False)
    prov = cfg.provider.lower()
    if prov == "openai":
        return _openai_complete(cfg, content)
    if prov == "anthropic":
        return _anthropic_complete(cfg, content)
    raise ValueError(f"Unsupported LLM provider: {cfg.provider}")
