"""Git operations module for retrieving diffs."""

import subprocess
from typing import List


def run_git_command(args: list[str]) -> str:
	"""
	Execute a git command and return the output.

	Args:
		args: Command arguments (without 'git' prefix)

	Returns:
		Command output as string

	Raises:
		RuntimeError: If the git command fails
	"""
	result = subprocess.run(
		["git", *args],
		capture_output=True,
		text=True,
		encoding="utf-8",
		errors="replace",
	)

	if result.returncode != 0:
		command_text = "git " + " ".join(args)
		raise RuntimeError(result.stderr.strip() or f"Failed to run {command_text}")

	return result.stdout


def get_git_diff() -> str:
	"""
	Retrieve both staged and unstaged git diff.

	Returns:
		Combined diff text (staged + unstaged)

	Raises:
		RuntimeError: If git operations fail
	"""
	staged_diff = run_git_command(["diff", "--cached"])
	unstaged_diff = run_git_command(["diff"])

	parts = [part for part in (staged_diff, unstaged_diff) if part.strip()]
	if not parts:
		return ""

	return "\n".join(parts).strip() + "\n"
