"""GitHub issue retrieval module for prompt augmentation."""

import json
from dataclasses import dataclass
from typing import Iterable, Sequence
from urllib import error, request


@dataclass(frozen=True)
class IssueRef:
    """Resolved issue reference for GitHub API calls."""

    owner: str
    repo: str
    number: int
    original_reference: str


def build_issue_context(
    issue_references: str,
    *,
    default_owner: str,
    default_repo: str,
    github_resources: Sequence[dict[str, str]],
) -> str:
    """
    Build RAG context text by fetching GitHub issue details.

    Returns empty string when references are unavailable or cannot be resolved.
    """
    refs = list(
        _resolve_issue_references(
            issue_references,
            default_owner=default_owner,
            default_repo=default_repo,
        )
    )
    if not refs:
        return ""

    sections: list[str] = []
    for ref in refs:
        github_token = select_github_token(ref, github_resources)
        issue = _fetch_issue(ref, github_token=github_token)
        if not issue:
            continue

        title = str(issue.get("title") or "").strip()
        body = str(issue.get("body") or "").strip()
        state = str(issue.get("state") or "").strip()
        html_url = str(issue.get("html_url") or "").strip()

        trimmed_body = _trim_text(body, max_chars=2000)
        sections.append(
            "\n".join(
                [
                    f"Reference: {ref.original_reference}",
                    f"Issue: {ref.owner}/{ref.repo}#{ref.number}",
                    f"State: {state}",
                    f"Title: {title}",
                    f"URL: {html_url}",
                    "Body:",
                    trimmed_body or "(empty)",
                ]
            )
        )

    if not sections:
        return ""

    return "\n\n---\n\n".join(sections)


def select_github_token(
    ref: IssueRef, github_resources: Sequence[dict[str, str]]
) -> str:
    """Select the best matching GitHub token for a repository."""
    exact_full_name = f"{ref.owner}/{ref.repo}".lower()
    owner_name = ref.owner.lower()
    repo_name = ref.repo.lower()
    fallback_token = ""

    for resource in github_resources:
        name = str(resource.get("name") or "").strip().lower()
        token = str(resource.get("api_key") or "").strip()
        if not name or not token:
            continue
        if name == exact_full_name:
            return token
        if name == owner_name or name == repo_name:
            fallback_token = token
        if name == "*" and not fallback_token:
            fallback_token = token

    return fallback_token


def _resolve_issue_references(
    issue_references: str,
    *,
    default_owner: str,
    default_repo: str,
) -> Iterable[IssueRef]:
    """Resolve space-separated references into owner/repo/number tuples."""
    seen: set[tuple[str, str, int]] = set()
    for token in issue_references.split():
        token = token.strip()
        if not token or "#" not in token:
            continue

        prefix, number_text = token.rsplit("#", 1)
        try:
            number = int(number_text)
        except ValueError:
            continue
        if number <= 0:
            continue

        owner = default_owner
        repo = default_repo

        if not prefix:
            pass
        elif "/" in prefix:
            owner_candidate, repo_candidate = prefix.split("/", 1)
            if owner_candidate and repo_candidate:
                owner, repo = owner_candidate, repo_candidate
        elif default_owner:
            repo = prefix
        else:
            continue

        if not owner or not repo:
            continue

        key = (owner, repo, number)
        if key in seen:
            continue
        seen.add(key)
        yield IssueRef(
            owner=owner,
            repo=repo,
            number=number,
            original_reference=token,
        )


def _fetch_issue(ref: IssueRef, *, github_token: str) -> dict[str, object] | None:
    """Fetch an issue object from GitHub REST API."""
    url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}/issues/{ref.number}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "ai-commit",
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    request_obj = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(request_obj, timeout=10) as response:
            payload = response.read().decode("utf-8", errors="replace")
            data = json.loads(payload)
    except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None
    return data


def _trim_text(text: str, *, max_chars: int) -> str:
    """Trim text to a bounded size for prompt usage."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n...(truncated)"