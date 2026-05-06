from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from modules.ai_client import generate_commit_message
from modules.config import _normalize_api_config


class OpenAIConfigTests(unittest.TestCase):
    def test_nested_config_reads_reasoning_effort(self) -> None:
        app_config = _normalize_api_config(
            {
                "openai": {
                    "api_url": "https://api.openai.com/v1",
                    "model": "gpt-5.4-mini",
                    "reasoning_effort": "low",
                    "api_key": "test-key",
                }
            },
            config_path=Path("api.json"),
        )

        self.assertEqual(app_config.openai.model, "gpt-5.4-mini")
        self.assertEqual(app_config.openai.reasoning_effort, "low")

    def test_generate_commit_message_sends_reasoning_effort(self) -> None:
        openai_config = _normalize_api_config(
            {
                "openai": {
                    "api_url": "https://api.openai.com/v1",
                    "model": "gpt-5.4-mini",
                    "reasoning_effort": "low",
                    "api_key": "test-key",
                }
            },
            config_path=Path("api.json"),
        ).openai

        with patch("modules.ai_client.read_prompt_template") as read_prompt_template:
            with patch("modules.ai_client.OpenAI") as openai_class:
                read_prompt_template.side_effect = ["system prompt", "diff:\n{{DIFF_TEXT}}"]
                openai_class.return_value.responses.create.return_value = SimpleNamespace(
                    output_text="feat: add support"
                )

                message = generate_commit_message(openai_config, "sample diff")

        self.assertEqual(message, "feat: add support")
        openai_class.return_value.responses.create.assert_called_once_with(
            model="gpt-5.4-mini",
            input=[
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "diff:\nsample diff"},
            ],
            store=False,
            reasoning={"effort": "low"},
        )


if __name__ == "__main__":
    unittest.main()