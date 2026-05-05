"""Commit message processing and formatting module."""

import re
from typing import Pattern


CONVENTIONAL_SUBJECT_PATTERN: Pattern[str] = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: .+"
)

SUBJECT_WITH_OPTIONAL_SCOPE_PATTERN: Pattern[str] = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(([^)]+)\))?(!)?:\s+(.+)$"
)

BOLD_SUBJECT_PATTERN: Pattern[str] = re.compile(r"\*\*([^:]+?):\s*(.+)")

# Matches a parenthesized issue reference such as (#123), (repo#123), or (owner/repo#123)
PARENTHESIZED_ISSUE_REF_PATTERN: Pattern[str] = re.compile(
    r"\(([\w/.-]*#\d+)\)"
)

# Matches an issue reference followed by trailing punctuation (e.g. #123. or #123,)
ISSUE_REF_TRAILING_PUNCT_PATTERN: Pattern[str] = re.compile(
    r"([\w/.-]*#\d+)[.,;:!?]+"
)

MAX_SUBJECT_WORDS = 16


def normalize_conventional_commit_message(message: str) -> str:
    """
    Ensure commit message follows Conventional Commits format.

    Args:
            message: Raw commit message

    Returns:
            Normalized commit message with valid type prefix

    Raises:
            ValueError: If message is empty after processing
    """
    text = remove_all_code_fences(message).strip()
    if not text:
        return ""

    lines = text.splitlines()
    subject = _select_subject_candidate(lines, original_message=message)

    if not CONVENTIONAL_SUBJECT_PATTERN.fullmatch(subject):
        subject = build_fallback_conventional_subject(subject)

    subject = subject.rstrip(".")
    subject, extracted_scope = remove_scope_from_subject(subject)

    body_lines = _strip_blank_edge_lines([line.rstrip() for line in lines[1:]])

    if extracted_scope and not has_scope_line(body_lines):
        body_lines = (
            [f"Scope: {extracted_scope}", "", *body_lines]
            if body_lines
            else [f"Scope: {extracted_scope}"]
        )

    subject, body_lines = _trim_subject_to_word_limit(subject, body_lines)

    if not body_lines:
        return subject

    return "\n".join([subject, "", *body_lines]).strip()


def _select_subject_candidate(lines: list[str], *, original_message: str) -> str:
    """Return the best subject line candidate from parsed lines."""
    candidate = sanitize_subject_line(lines[0].strip())
    subject: str | None = None
    if (
        len(candidate) >= 5
        and any(c.isalpha() for c in candidate)
        and not candidate.startswith("chore: ")
    ):
        subject = candidate
        if len(subject) >= 15:
            return subject

    for original_line in original_message.splitlines():
        bold_candidate = _extract_markdown_bold_subject_candidate(original_line)
        if bold_candidate:
            return bold_candidate

    if not subject:
        for line in lines[1:]:
            candidate = sanitize_subject_line(re.sub(r"\*+", "", line.strip()))
            if len(candidate) >= 5 and any(c.isalpha() for c in candidate):
                return candidate

    return subject or "chore: update changes"


def _strip_blank_edge_lines(lines: list[str]) -> list[str]:
    """Remove leading and trailing blank lines in-place and return the list."""
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def remove_scope_from_subject(subject: str) -> tuple[str, str | None]:
    """
    Convert subject from type(scope): text to type: text and return extracted scope.

    Args:
            subject: Normalized subject line

    Returns:
            Tuple of (subject_without_scope, extracted_scope_or_none)
    """
    match = SUBJECT_WITH_OPTIONAL_SCOPE_PATTERN.fullmatch(subject.strip())
    if not match:
        return subject, None

    commit_type = match.group(1)
    scope = match.group(3)
    breaking_mark = match.group(4) or ""
    summary = match.group(5).strip()

    if scope:
        return f"{commit_type}{breaking_mark}: {summary}", scope.strip()

    return subject, None


def has_scope_line(body_lines: list[str]) -> bool:
    """Return True if body already contains a Scope: line."""
    return any(line.strip().lower().startswith("scope:") for line in body_lines)


def build_fallback_conventional_subject(subject: str) -> str:
    """
    Create a fallback subject line with 'chore:' type prefix.

    Args:
            subject: Original subject text

    Returns:
            Subject with 'chore:' prefix
    """
    text = sanitize_subject_line(subject).strip()
    if not text:
        return "chore: update changes"

    if text[0].isupper():
        text = text[0].lower() + text[1:]

    return f"chore: {text}"


def sanitize_subject_line(subject: str) -> str:
    """
    Remove problematic characters and code fences from subject line.

    Args:
            subject: Original subject text

    Returns:
            Sanitized subject line
    """
    text = subject.strip()
    text = re.sub(r"```\w*", "", text).strip()
    text = re.sub(r"`+", "", text).strip()
    return text


def _trim_subject_to_word_limit(
    subject: str, body_lines: list[str], max_words: int = MAX_SUBJECT_WORDS
) -> tuple[str, list[str]]:
    """
    Trim subject to at most max_words words.

    If the subject exceeds max_words, the overflow words are prepended to
    body_lines so no information is lost.
    """
    words = subject.split()
    if len(words) <= max_words:
        return subject, body_lines

    trimmed = " ".join(words[:max_words])
    overflow = " ".join(words[max_words:])
    new_body = [overflow, "", *body_lines] if body_lines else [overflow]
    return trimmed, new_body


def _extract_markdown_bold_subject_candidate(line: str) -> str:
    """Extract one subject candidate from markdown bold format."""
    bold_match = BOLD_SUBJECT_PATTERN.search(line)
    if not bold_match:
        return ""

    part1 = bold_match.group(1).strip()
    part2 = bold_match.group(2).strip().lstrip("*").strip()
    candidate = sanitize_subject_line(part1 + ": " + part2)
    return candidate if len(candidate) >= 5 else ""


def remove_all_code_fences(text: str) -> str:
    """
    Remove ALL markdown code fences (```) from text.

    Args:
            text: Text possibly containing code fences

    Returns:
            Text with all code fences removed
    """
    result = re.sub(r"```\w*", "", text)
    result = re.sub(r"`+", "", result)
    result = re.sub(r"\n\s*\n+", "\n\n", result)
    return result.strip()


def append_issue_reference_to_subject(message: str, issue_reference: str) -> str:
    """
    Append issue reference to the subject line (first line) of commit message.

    If the subject already contains the issue reference (possibly wrapped in
    parentheses), the parentheses are removed and no duplicate reference is
    appended.

    Args:
            message: Commit message
            issue_reference: Issue reference like '#42', 'repo#4242', or 'owner/repo#4242'

    Returns:
            Message with issue reference appended to subject line
    """
    if not issue_reference:
        return message

    lines = message.splitlines()
    if not lines:
        return message

    # Normalize parenthesized refs and trailing punctuation in both subject and ref
    subject = PARENTHESIZED_ISSUE_REF_PATTERN.sub(r"\1", lines[0].rstrip()).strip()
    subject = ISSUE_REF_TRAILING_PUNCT_PATTERN.sub(r"\1", subject).strip()
    issue_reference = ISSUE_REF_TRAILING_PUNCT_PATTERN.sub(r"\1", issue_reference).strip()

    if issue_reference in subject:
        lines[0] = subject
        return "\n".join(lines)

    lines[0] = f"{subject} {issue_reference}".strip()
    return "\n".join(lines)
