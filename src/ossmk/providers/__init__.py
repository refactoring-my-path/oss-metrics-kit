from __future__ import annotations

from typing import Protocol

from .github import GitHubProvider


class Provider(Protocol):
    id: str


def get_provider(name: str) -> Provider:
    if name == "github":
        return GitHubProvider()
    raise ValueError(f"Unknown provider: {name}")

__all__ = ["get_provider", "Provider"]
