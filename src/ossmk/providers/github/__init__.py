from __future__ import annotations

import json
from typing import Any, Iterable

import httpx

from ossmk.core.models import ContributionEvent, EventKind
from ossmk.storage.sqlite import HttpCache
from ossmk.utils import github_token_from_env, http_client, http_get, utcnow_iso


class GitHubProvider:
    id = "github"

    def __init__(self) -> None:
        self.cache = HttpCache()

    def _auth_headers(self) -> dict[str, str]:
        token = github_token_from_env()
        return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    def _cached_get_json(self, client: httpx.Client, url: str) -> list[dict[str, Any]]:
        headers = self._auth_headers()
        cached = self.cache.get(url)
        if cached and cached.get("etag"):
            headers["If-None-Match"] = cached["etag"]
        resp = http_get(client, url, headers=headers)
        if resp.status_code == 304 and cached:
            body = cached["body"]
        else:
            resp.raise_for_status()
            body = resp.text
            etag = resp.headers.get("ETag")
            last_modified = resp.headers.get("Last-Modified")
            self.cache.set(url, etag, last_modified, body, utcnow_iso())
        return json.loads(body)

    def fetch_repo_issues_and_prs(self, repo: str) -> list[ContributionEvent]:
        # repo format: owner/name
        owner, name = repo.split("/", 1)
        base_url = f"https://api.github.com/repos/{owner}/{name}/issues?state=all&per_page=100"
        events: list[ContributionEvent] = []
        with http_client() as client:
            data = self._cached_get_json(client, base_url)
        for item in data:
            kind = EventKind.pr if "pull_request" in item else EventKind.issue
            user = item.get("user") or {}
            events.append(
                ContributionEvent(
                    id=str(item["id"]),
                    kind=kind,
                    repo_id=f"github.com/{owner}/{name}",
                    user_id=str(user.get("login") or "unknown"),
                    created_at=item.get("created_at"),  # Pydantic will parse to datetime
                    lines_added=0,
                    lines_removed=0,
                )
            )
        return events

    def fetch_user_repos(self, login: str) -> list[str]:
        url = f"https://api.github.com/users/{login}/repos?per_page=100&type=owner&sort=updated"
        with http_client() as client:
            data = self._cached_get_json(client, url)
        full_names = [item.get("full_name") for item in data if item.get("full_name")]
        return [str(x) for x in full_names]

    def fetch_user_contributions(self, login: str, max_repos: int | None = 20) -> list[ContributionEvent]:
        repos = self.fetch_user_repos(login)
        if max_repos is not None:
            repos = repos[:max_repos]
        all_events: list[ContributionEvent] = []
        for repo in repos:
            try:
                all_events.extend(self.fetch_repo_issues_and_prs(repo))
            except httpx.HTTPStatusError as e:
                # skip inaccessible repos gracefully
                continue
        return all_events


provider = GitHubProvider()
