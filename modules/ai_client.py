"""AI API client module for generating commit messages."""

import itertools
import sys
import threading
from pathlib import Path
from typing import Any

from openai import OpenAI

from modules.config import OpenAIConfig


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def generate_commit_message(
    openai_config: OpenAIConfig,
    diff_text: str,
    issue_context: str = "",
) -> str:
    """
    Generate a commit message from git diff using AI API.

    Args:
            openai_config: OpenAI-compatible API configuration
            diff_text: Git diff content
            issue_context: Optional issue context for RAG

    Returns:
            Generated commit message

    Raises:
            RuntimeError: If API request fails or message is empty
    """
    base_url = normalize_provider_base_url(openai_config.api_url)
    client = OpenAI(api_key=openai_config.api_key, base_url=base_url)
    system_prompt = read_prompt_template("system_prompt.txt")
    user_prompt = build_user_prompt(diff_text, issue_context=issue_context)

    input_items = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]

    try:
        request_args = {
            "model": openai_config.model,
            "input": input_items,
            "store": False,
        }
        if openai_config.reasoning_effort is not None:
            request_args["reasoning"] = {"effort": openai_config.reasoning_effort}

        with _ProgressIndicator():
            response = client.responses.create(**request_args)
        content = extract_text_from_response(response)
    except Exception as exc:
        responses_url = f"{base_url}/responses"
        raise RuntimeError(f"API request failed ({responses_url}): {exc}") from exc

    message = (content or "").strip()
    if not message:
        raise RuntimeError("Generated commit message is empty")

    return message


def extract_text_from_response(response: Any) -> str:
    """
    Extract text content from API response object.

    Handles both direct output_text attribute and nested output array.

    Args:
            response: API response object

    Returns:
            Extracted text content
    """
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output_items = getattr(response, "output", None)
    if not isinstance(output_items, list):
        return ""

    parts = []
    for item in output_items:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", []):
            if getattr(content, "type", None) == "output_text":
                text = getattr(content, "text", "")
                if text:
                    parts.append(text)

    return "\n".join(parts)


def build_user_prompt(diff_text: str, *, issue_context: str = "") -> str:
    """Build user prompt by injecting git diff into template."""
    template = read_prompt_template("user_prompt.txt")
    prompt = template.replace("{{DIFF_TEXT}}", diff_text)
    context = issue_context.strip()
    if not context:
        return prompt

    return (
        prompt
        + "\n\nGitHub issue context (RAG). Use this only as supplemental evidence:\n"
        + context
    )


def read_prompt_template(file_name: str) -> str:
    """Read prompt template text from repository-level prompts directory."""
    path = PROMPTS_DIR / file_name
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise RuntimeError(f"Prompt file not found: {path}") from exc


def normalize_provider_base_url(api_url: str) -> str:
    """
    Extract base URL by removing API endpoint-specific paths.

    Args:
            api_url: Full or partial API URL

    Returns:
            Base URL without endpoint-specific paths
    """
    url = api_url.rstrip("/")
    for suffix in ("/chat/completions", "/responses"):
        if url.endswith(suffix):
            return url[: -len(suffix)]

    return url


_SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


class _ProgressIndicator:
    """Show a spinner on the console while active, then clear it."""

    def __init__(self, *, stream=None) -> None:
        self._stream = stream or sys.stderr
        self._stop_event = threading.Event()
        self._thread = None

    def __enter__(self) -> "_ProgressIndicator":
        self._thread = threading.Thread(
            target=self._spin,
            name="progress-indicator",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
        self._clear()

    def _spin(self) -> None:
        for frame in itertools.cycle(_SPINNER_FRAMES):
            if self._stop_event.is_set():
                return
            self._stream.write("\r" + frame)
            self._stream.flush()
            self._stop_event.wait(0.1)

    def _clear(self) -> None:
        self._stream.write("\r" + " " * 2)
        self._stream.write("\r")
        self._stream.flush()
