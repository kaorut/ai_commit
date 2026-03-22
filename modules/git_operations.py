"""Git operations module for retrieving diffs."""

import subprocess
from typing import Sequence


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


def get_git_diff(include_unstaged: bool = False) -> str:
	"""
	Retrieve git diff text for commit message generation.

	When include_unstaged is False, only staged changes are included.
	When include_unstaged is True, both staged and unstaged changes are included.

	Args:
		include_unstaged: Include unstaged changes when True

	Returns:
		Diff text for prompt generation

	Raises:
		RuntimeError: If git operations fail
	"""
	staged_diff = run_git_command(["diff", "--cached"])

	parts = [part for part in (staged_diff,) if part.strip()]
	if include_unstaged:
		unstaged_diff = run_git_command(["diff"])
		if unstaged_diff.strip():
			parts.append(unstaged_diff)

	if not parts:
		return ""

	return "\n".join(parts).strip() + "\n"


def commit_with_message(message: str, commit_options: Sequence[str]) -> None:
	"""
	Run git commit with the provided message and pass-through options.

	Args:
		message: Commit message text
		commit_options: git commit options (must start with '-' or '--')

	Raises:
		RuntimeError: If commit message is empty or commit command fails
	"""
	text = message.strip()
	if not text:
		raise RuntimeError("Commit message is empty")

	command = ["git", "commit", *commit_options, "-F", "-"]
	result = subprocess.run(
		command,
		input=text + "\n",
		capture_output=True,
		text=True,
		encoding="utf-8",
		errors="replace",
	)

	if result.returncode != 0:
		raise RuntimeError(result.stderr.strip() or "git commit failed")
