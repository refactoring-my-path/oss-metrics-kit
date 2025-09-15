from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from ossmk.core.models import ContributionEvent, EventKind
from ossmk.storage.sqlite import HttpCache
from ossmk.utils import (
    github_token_from_env,
    http_client,
    http_get,
    utcnow_iso,
    parse_link_next,
    parse_since,
    http_async_client,
    http_get_async,
    is_bot_login,
)
import os


class GitHubProvider:
    id = "github"

    def __init__(self) -> None:
        self.cache = HttpCache()

    def _auth_headers(self) -> dict[str, str]:
        token = github_token_from_env()
        return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    def _cached_get_json(self, client: httpx.Client, url: str) -> tuple[list[dict[str, Any]], str | None, httpx.Response]:
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
        data = json.loads(body)
        next_url = parse_link_next(resp.headers.get("Link"))
        return data, next_url, resp

    async def _cached_get_json_async(
        self, client: httpx.AsyncClient, url: str
    ) -> tuple[list[dict[str, Any]], str | None, httpx.Response]:
        headers = self._auth_headers()
        cached = self.cache.get(url)
        if cached and cached.get("etag"):
            headers["If-None-Match"] = cached["etag"]
        resp = await http_get_async(client, url, headers=headers)
        if resp.status_code == 304 and cached:
            body = cached["body"]
        else:
            resp.raise_for_status()
            body = resp.text
            etag = resp.headers.get("ETag")
            last_modified = resp.headers.get("Last-Modified")
            self.cache.set(url, etag, last_modified, body, utcnow_iso())
        data = json.loads(body)
        next_url = parse_link_next(resp.headers.get("Link"))
        return data, next_url, resp

    def fetch_repo_issues_and_prs(self, repo: str) -> list[ContributionEvent]:
        owner, name = repo.split("/", 1)
        base_url = f"https://api.github.com/repos/{owner}/{name}/issues?state=all&per_page=100"
        events: list[ContributionEvent] = []
        with http_client() as client:
            url = base_url
            while True:
                data, next_url, _ = self._cached_get_json(client, url)
                for item in data:
                    kind = EventKind.pr if "pull_request" in item else EventKind.issue
                    user = item.get("user") or {}
                    events.append(
                        ContributionEvent(
                            id=str(item["id"]),
                            kind=kind,
                            repo_id=f"github.com/{owner}/{name}",
                            user_id=str(user.get("login") or "unknown"),
                            created_at=item.get("created_at"),
                            lines_added=0,
                            lines_removed=0,
                        )
                    )
                if not next_url:
                    break
                url = next_url
        return events

    def fetch_repo_commits(self, repo: str, since: str | None = None) -> list[ContributionEvent]:
        owner, name = repo.split("/", 1)
        params = "per_page=100"
        iso_since = parse_since(since)
        if iso_since:
            qp = httpx.QueryParams({"since": iso_since})
            params += f"&{qp}"
        base_url = f"https://api.github.com/repos/{owner}/{name}/commits?{params}"
        events: list[ContributionEvent] = []
        with http_client() as client:
            url = base_url
            while True:
                data, next_url, _ = self._cached_get_json(client, url)
                for c in data:
                    author = (c.get("author") or {}).get("login") or (c.get("committer") or {}).get("login") or "unknown"
                    if os.getenv("OSSMK_EXCLUDE_BOTS", "1") == "1" and is_bot_login(author):
                        continue
                    events.append(
                        ContributionEvent(
                            id=str(c.get("sha")),
                            kind=EventKind.commit,
                            repo_id=f"github.com/{owner}/{name}",
                            user_id=str(author),
                            created_at=(c.get("commit") or {}).get("author", {}).get("date"),
                            lines_added=0,
                            lines_removed=0,
                        )
                    )
                if not next_url:
                    break
                url = next_url
        return events

    def fetch_repo_pr_reviews(self, repo: str, max_prs: int | None = 50) -> list[ContributionEvent]:
        owner, name = repo.split("/", 1)
        pr_url = f"https://api.github.com/repos/{owner}/{name}/pulls?state=all&per_page=100&sort=updated"
        events: list[ContributionEvent] = []
        prs: list[dict[str, Any]] = []
        with http_client() as client:
            url = pr_url
            while True and (max_prs is None or len(prs) < max_prs):
                data, next_url, _ = self._cached_get_json(client, url)
                prs.extend(data)
                if not next_url or (max_prs is not None and len(prs) >= max_prs):
                    break
                url = next_url
            for pr in prs[: (max_prs or len(prs))]:
                num = pr.get("number")
                if not num:
                    continue
                reviews_url = f"https://api.github.com/repos/{owner}/{name}/pulls/{num}/reviews?per_page=100"
                url = reviews_url
                while True:
                    data, next_url, _ = self._cached_get_json(client, url)
                    for rv in data:
                        user = (rv.get("user") or {}).get("login") or "unknown"
                        if os.getenv("OSSMK_EXCLUDE_BOTS", "1") == "1" and is_bot_login(user):
                            continue
                        events.append(
                            ContributionEvent(
                                id=str(rv.get("id")),
                                kind=EventKind.review,
                                repo_id=f"github.com/{owner}/{name}",
                                user_id=str(user),
                                created_at=rv.get("submitted_at") or rv.get("created_at"),
                                lines_added=0,
                                lines_removed=0,
                            )
                        )
                    if not next_url:
                        break
                    url = next_url
        return events

    def fetch_user_repos(self, login: str) -> list[str]:
        url = f"https://api.github.com/users/{login}/repos?per_page=100&type=owner&sort=updated"
        with http_client() as client:
            data, _, _ = self._cached_get_json(client, url)
        full_names = [item.get("full_name") for item in data if item.get("full_name")]
        return [str(x) for x in full_names]

    def fetch_user_contributions(self, login: str, max_repos: int | None = 20, since: str | None = None) -> list[ContributionEvent]:
        repos = self.fetch_user_repos(login)
        if max_repos is not None:
            repos = repos[:max_repos]
        all_events: list[ContributionEvent] = []
        for repo in repos:
            try:
                all_events.extend(self.fetch_repo_issues_and_prs(repo))
                all_events.extend(self.fetch_repo_commits(repo, since=since))
                all_events.extend(self.fetch_repo_pr_reviews(repo))
            except httpx.HTTPStatusError:
                continue
        return all_events

    async def fetch_user_contributions_async(
        self, login: str, max_repos: int | None = 20, since: str | None = None
    ) -> list[ContributionEvent]:
        repos = self.fetch_user_repos(login)
        if max_repos is not None:
            repos = repos[:max_repos]
        try:
            conc = int(os.getenv("OSSMK_CONCURRENCY", "5"))
        except Exception:
            conc = 5
        semaphore = asyncio.Semaphore(max(1, min(conc, 20)))
        events: list[ContributionEvent] = []

        async def fetch_repo(repo: str) -> None:
            async with semaphore:
                try:
                    e1 = await self._fetch_repo_commits_async(repo, since=since)
                    e2 = await self._fetch_repo_reviews_async(repo)
                    e0 = self.fetch_repo_issues_and_prs(repo)
                    events.extend(e0)
                    events.extend(e1)
                    events.extend(e2)
                except Exception:
                    return

        await asyncio.gather(*(fetch_repo(r) for r in repos))
        return events

    async def _fetch_repo_commits_async(self, repo: str, since: str | None = None) -> list[ContributionEvent]:
        owner, name = repo.split("/", 1)
        params = "per_page=100"
        iso_since = parse_since(since)
        if iso_since:
            qp = httpx.QueryParams({"since": iso_since})
            params += f"&{qp}"
        base_url = f"https://api.github.com/repos/{owner}/{name}/commits?{params}"
        events: list[ContributionEvent] = []
        async with http_async_client() as client:
            url = base_url
            while True:
                data, next_url, _ = await self._cached_get_json_async(client, url)
                for c in data:
                    author = (c.get("author") or {}).get("login") or (c.get("committer") or {}).get("login") or "unknown"
                    events.append(
                        ContributionEvent(
                            id=str(c.get("sha")),
                            kind=EventKind.commit,
                            repo_id=f"github.com/{owner}/{name}",
                            user_id=str(author),
                            created_at=(c.get("commit") or {}).get("author", {}).get("date"),
                            lines_added=0,
                            lines_removed=0,
                        )
                    )
                if not next_url:
                    break
                url = next_url
        return events

    async def _fetch_repo_reviews_async(self, repo: str, max_prs: int | None = 50) -> list[ContributionEvent]:
        owner, name = repo.split("/", 1)
        pr_url = f"https://api.github.com/repos/{owner}/{name}/pulls?state=all&per_page=100&sort=updated"
        events: list[ContributionEvent] = []
        prs: list[dict[str, Any]] = []
        async with http_async_client() as client:
            url = pr_url
            while True and (max_prs is None or len(prs) < max_prs):
                data, next_url, _ = await self._cached_get_json_async(client, url)
                prs.extend(data)
                if not next_url or (max_prs is not None and len(prs) >= max_prs):
                    break
                url = next_url
            for pr in prs[: (max_prs or len(prs))]:
                num = pr.get("number")
                if not num:
                    continue
                reviews_url = f"https://api.github.com/repos/{owner}/{name}/pulls/{num}/reviews?per_page=100"
                url = reviews_url
                while True:
                    data, next_url, _ = await self._cached_get_json_async(client, url)
                    for rv in data:
                        user = (rv.get("user") or {}).get("login") or "unknown"
                        events.append(
                            ContributionEvent(
                                id=str(rv.get("id")),
                                kind=EventKind.review,
                                repo_id=f"github.com/{owner}/{name}",
                                user_id=str(user),
                                created_at=rv.get("submitted_at") or rv.get("created_at"),
                                lines_added=0,
                                lines_removed=0,
                            )
                        )
                    if not next_url:
                        break
                    url = next_url
        return events

    async def fetch_user_contributions_graphql_async(
        self, login: str, since: str | None = None
    ) -> list[ContributionEvent]:
        url = "https://api.github.com/graphql"
        headers = self._auth_headers()
        # Cursor-paginated search for PRs and Issues authored by login
        query = (
            "query($q:String!, $after:String){"
            "  search(type: ISSUE, query: $q, first: 100, after: $after){"
            "    pageInfo{ hasNextPage endCursor }"
            "    nodes {"
            "      ... on PullRequest { id number repository { nameWithOwner } author { login } createdAt }"
            "      ... on Issue { id number repository { nameWithOwner } author { login } createdAt }"
            "    }"
            "  }"
            "}"
        )
        q_base = f"author:{login} is:public"
        events: list[ContributionEvent] = []
        async with http_async_client() as client:
            after = None
            while True:
                payload = {"query": query, "variables": {"q": q_base, "after": after}}
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json().get("data") or {}
                search = data.get("search") or {}
                nodes = search.get("nodes") or []
                for n in nodes:
                    repo = (n.get("repository") or {}).get("nameWithOwner") or "unknown/unknown"
                    is_pr = "number" in n and (n.get("__typename", "") == "PullRequest" or "id" in n)
                    kind = EventKind.pr if "PullRequest" in str(n) else (EventKind.issue)
                    events.append(
                        ContributionEvent(
                            id=str(n.get("id")),
                            kind=kind,
                            repo_id=f"github.com/{repo}",
                            user_id=str(((n.get("author") or {}).get("login")) or login),
                            created_at=n.get("createdAt"),
                            lines_added=0,
                            lines_removed=0,
                        )
                    )
                page = search.get("pageInfo") or {}
                if not page.get("hasNextPage"):
                    break
                after = page.get("endCursor")
        return events
