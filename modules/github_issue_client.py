"""GitHub issue retrieval module for prompt augmentation."""

import json
from dataclasses import dataclass
from typing import Iterable, Sequence
from urllib import error, request

from modules.config import GitHubResource


GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"
GITHUB_USER_AGENT = "ai-commit"
GITHUB_TIMEOUT_SECONDS = 10


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
    github_resources: Sequence[GitHubResource],
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

    sections = _build_issue_sections(refs, github_resources=github_resources)

    if not sections:
        return ""

    return "\n\n---\n\n".join(sections)


def _build_issue_sections(
    refs: Sequence[IssueRef],
    *,
    github_resources: Sequence[GitHubResource],
) -> list[str]:
    """Fetch and format issue sections for all resolved references."""
    sections: list[str] = []
    for ref in refs:
        section = _build_issue_section(ref, github_resources=github_resources)
        if section:
            sections.append(section)
    return sections


def _build_issue_section(
    ref: IssueRef,
    *,
    github_resources: Sequence[GitHubResource],
) -> str:
    """Fetch and format one issue section."""
    github_token = select_github_token(ref, github_resources)
    issue = _fetch_issue(ref, github_token=github_token)
    if not issue:
        return ""
    return _format_issue_section(ref, issue)


def select_github_token(
    ref: IssueRef, github_resources: Sequence[GitHubResource]
) -> str:
    """Select the best matching GitHub token for a repository."""
    best_resource = _select_best_resource(ref, github_resources)
    if best_resource is None:
        return ""

    return best_resource.api_key


def _select_best_resource(
    ref: IssueRef,
    github_resources: Sequence[GitHubResource],
) -> GitHubResource | None:
    """Return best matching resource by selector priority.

    If multiple resources share the same priority, the first declared entry wins.
    """
    best_resource: GitHubResource | None = None
    best_priority = 0

    for resource in github_resources:
        priority = resource.priority(ref.owner, ref.repo)
        if priority <= 0:
            continue

        # Why not replace on equal priority: config order should stay authoritative.
        if priority > best_priority:
            best_priority = priority
            best_resource = resource

    return best_resource


def _format_issue_section(ref: IssueRef, issue: dict[str, object]) -> str:
    """Format one fetched issue as RAG text."""
    title = _get_issue_text(issue, "title")
    body = _get_issue_text(issue, "body")
    state = _get_issue_text(issue, "state")
    html_url = _get_issue_text(issue, "html_url")

    return "\n".join(
        [
            f"Reference: {ref.original_reference}",
            f"Issue: {ref.owner}/{ref.repo}#{ref.number}",
            f"State: {state}",
            f"Title: {title}",
            f"URL: {html_url}",
            "Body:",
            _trim_text(body, max_chars=2000) or "(empty)",
        ]
    )


def _get_issue_text(issue: dict[str, object], key: str) -> str:
    """Return one text field from a GitHub issue payload."""
    return str(issue.get(key) or "").strip()


def _resolve_issue_references(
    issue_references: str,
    *,
    default_owner: str,
    default_repo: str,
) -> Iterable[IssueRef]:
    """Resolve space-separated references into owner/repo/number tuples."""
    seen: set[tuple[str, str, int]] = set()
    for token in issue_references.split():
        resolved_ref = _resolve_issue_token(
            token,
            default_owner=default_owner,
            default_repo=default_repo,
        )
        if resolved_ref is None:
            continue

        key = (resolved_ref.owner, resolved_ref.repo, resolved_ref.number)
        if key in seen:
            continue
        seen.add(key)
        yield resolved_ref


def _resolve_issue_token(
    token: str,
    *,
    default_owner: str,
    default_repo: str,
) -> IssueRef | None:
    """Resolve one issue token into owner/repo/number."""
    value = token.strip()
    if not value or "#" not in value:
        return None

    prefix, number_text = value.rsplit("#", 1)
    try:
        number = int(number_text)
    except ValueError:
        return None
    if number <= 0:
        return None

    owner, repo = _resolve_issue_location(
        prefix,
        default_owner=default_owner,
        default_repo=default_repo,
    )
    if not owner or not repo:
        return None

    return IssueRef(
        owner=owner,
        repo=repo,
        number=number,
        original_reference=value,
    )


def _resolve_issue_location(
    prefix: str,
    *,
    default_owner: str,
    default_repo: str,
) -> tuple[str, str]:
    """Resolve owner/repo from token prefix and defaults."""
    owner = default_owner
    repo = default_repo

    if not prefix:
        return owner, repo

    if "/" in prefix:
        owner_candidate, repo_candidate = prefix.split("/", 1)
        if owner_candidate and repo_candidate:
            return owner_candidate, repo_candidate
        return "", ""

    if not default_owner:
        return "", ""

    return default_owner, prefix


def _fetch_issue(ref: IssueRef, *, github_token: str) -> dict[str, object] | None:
    """Fetch an issue object from GitHub REST API."""
    request_obj = _build_issue_request(ref, github_token=github_token)
    try:
        with request.urlopen(request_obj, timeout=GITHUB_TIMEOUT_SECONDS) as response:
            payload = response.read().decode("utf-8", errors="replace")
            data = json.loads(payload)
    except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None
    return data


def _build_issue_request(ref: IssueRef, *, github_token: str) -> request.Request:
    """Build one authenticated GitHub issue request."""
    url = f"{GITHUB_API_BASE_URL}/repos/{ref.owner}/{ref.repo}/issues/{ref.number}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": GITHUB_USER_AGENT,
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    return request.Request(url, headers=headers, method="GET")


def _trim_text(text: str, *, max_chars: int) -> str:
    """Trim text to a bounded size for prompt usage."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n...(truncated)"