"""Commit message processing and formatting module."""

import re
from typing import Pattern


CONVENTIONAL_SUBJECT_PATTERN: Pattern[str] = re.compile(
	r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: .+"
)


def strip_surrounding_code_fence(text: str) -> str:
	"""
	Remove markdown code fence wrappers (```) from text.

	Args:
		text: Original text possibly wrapped in code fence

	Returns:
		Text without surrounding code fences
	"""
	stripped = text.strip()
	if not stripped.startswith("```"):
		return stripped

	lines = stripped.splitlines()
	if len(lines) < 3:
		return stripped

	if not lines[0].startswith("```"):
		return stripped

	if lines[-1].strip() != "```":
		return stripped

	inner_text = "\n".join(lines[1:-1]).strip()
	return inner_text


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
	text = message.strip()
	if not text:
		return ""

	lines = text.splitlines()
	subject = lines[0].strip()
	
	if not CONVENTIONAL_SUBJECT_PATTERN.fullmatch(subject):
		subject = build_fallback_conventional_subject(subject)

	body_lines = [line.rstrip() for line in lines[1:]]
	if body_lines:
		while body_lines and not body_lines[0].strip():
			body_lines.pop(0)
		while body_lines and not body_lines[-1].strip():
			body_lines.pop()

	if not body_lines:
		return subject

	return "\n".join([subject, "", *body_lines]).strip()


def build_fallback_conventional_subject(subject: str) -> str:
	"""
	Create a fallback subject line with 'chore:' type prefix.

	Args:
		subject: Original subject text

	Returns:
		Subject with 'chore:' prefix
	"""
	text = subject.strip()
	if not text:
		return "chore: update changes"

	if text[0].isupper():
		text = text[0].lower() + text[1:]

	return f"chore: {text}"


def append_issue_reference_to_subject(message: str, issue_reference: str) -> str:
	"""
	Append issue reference to the subject line (first line) of commit message.

	Args:
		message: Commit message
		issue_reference: Issue reference like '#42' or 'otherproject#4242'

	Returns:
		Message with issue reference appended to subject line
	"""
	if not issue_reference:
		return message

	lines = message.splitlines()
	if not lines:
		return message

	lines[0] = f"{lines[0].rstrip()} {issue_reference}".strip()
	return "\n".join(lines)
