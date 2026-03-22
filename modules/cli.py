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

	parsed_args, remaining_args = parser.parse_known_args(args)
	parsed_args.issue_reference = validate_issue_reference(parsed_args.issue_reference)

	non_option_args = [token for token in remaining_args if not token.startswith("-")]
	if non_option_args:
		raise ValueError(
			"Non-option arguments are not supported: " + " ".join(non_option_args)
		)

	parsed_args.commit_options = [
		token for token in remaining_args if token.startswith("-")
	]
	parsed_args.include_unstaged_for_diff = has_all_option(parsed_args.commit_options)
	return parsed_args


def has_all_option(commit_options: Sequence[str]) -> bool:
	"""Return True if commit options include -a or --all."""
	for option in commit_options:
		if option == "--all":
			return True
		if option.startswith("-") and not option.startswith("--") and "a" in option[1:]:
			return True
	return False


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
