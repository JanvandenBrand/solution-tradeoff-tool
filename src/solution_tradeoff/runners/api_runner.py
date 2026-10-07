"""ApiRunner — thin wrapper around the Anthropic SDK for running perspective sessions."""

import os
import re
from typing import Any

import anthropic

DEFAULT_MODEL = "claude-sonnet-5-5"
_MAX_TOKENS = 8096


class ApiRunner:
    """Calls the Claude API with a system prompt and user message.

    Reads ANTHROPIC_API_KEY from the environment.

    Args:
        model: Claude model ID to use.

    Raises:
        EnvironmentError: If ANTHROPIC_API_KEY is not set.
    """

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY environment variable not set.\n"
                "Export it before running: export ANTHROPIC_API_KEY=sk-ant-..."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def send(self, user: str, system: str | None = None) -> str:
        """Send a message and return the text response.

        Args:
            user: User message content.
            system: Optional system prompt.

        Returns:
            The model's text response.
        """
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": _MAX_TOKENS,
            "messages": [{"role": "user", "content": user}],
        }
        if system:
            kwargs["system"] = system
        message = self._client.messages.create(**kwargs)
        return str(message.content[0].text)


def extract_yaml(response: str) -> str:
    """Extract YAML content from a Claude response.

    Handles responses where the YAML is wrapped in a code fence (```yaml or ```),
    as well as raw YAML responses with no fencing.

    Args:
        response: Raw text response from the model.

    Returns:
        Extracted YAML string, stripped of surrounding whitespace.
    """
    match = re.search(r"```yaml\s*\n(.*?)```", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*\n(.*?)```", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response.strip()
