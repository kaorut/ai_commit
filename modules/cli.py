"""Command-line interface and argument parsing module."""

import argparse
import re
from typing import Sequence


def parse_arguments(args: Sequence[str]) -> argparse.Namespace:
	"""
	Parse command-line arguments.

	Args:
		args: Command-line arguments (typically sys.argv[1:])

	Returns:
		Parsed arguments namespace

	Raises:
		ValueError: If issue reference format is invalid
	"""
	parser = argparse.ArgumentParser(
		prog="gen_commit_msg.py",
		description="Generate a commit message from git diff using AI.",
	)
	parser.add_argument(
		"issue_reference",
		nargs="?",
		default="",
		help="Optional issue reference like '#42' or 'otherproject#4242'.",
	)

	parsed_args = parser.parse_args(args)
	parsed_args.issue_reference = validate_issue_reference(parsed_args.issue_reference)
	return parsed_args


def validate_issue_reference(issue_reference: str) -> str:
	"""
	Validate issue reference format.

	Accepted formats:
	- '#42' (bare issue number)
	- 'project#123' (project-prefixed)

	Args:
		issue_reference: Issue reference string

	Returns:
		Validated issue reference (empty string if not provided)

	Raises:
		ValueError: If format is invalid
	"""
	value = issue_reference.strip()
	if not value:
		return ""

	if not re.fullmatch(r"(?:[A-Za-z0-9_.-]+)?#\d+", value):
		raise ValueError("Issue reference must be like '#42' or 'otherproject#4242'")

	return value
