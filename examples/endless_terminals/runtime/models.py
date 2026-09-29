"""Explicit fixture or HTTP models, with no implicit retries."""

import json
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parent


class Model(Protocol):
    """One bounded completion per call, without implicit retries."""

    def complete(
        self, messages: list[dict[str, str]], timeout: float
    ) -> tuple[str, dict[str, Any]]:
        """Return assistant content and usage within the timeout.

        Args:
            messages: Chat history including the system instruction.
            timeout: Total request deadline in seconds.

        Returns:
            Assistant text and provider token counts.
        """
        ...


class FixtureModel:
    """Replay scripted responses to test the adapter without inference."""

    def __init__(self, responses: list[str]) -> None:
        """Configure scripted responses.

        Args:
            responses: Ordered assistant responses to replay.
        """
        self.responses = iter(responses)

    def complete(
        self, messages: list[dict[str, str]], timeout: float
    ) -> tuple[str, dict[str, Any]]:
        """Return the next scripted response.

        Args:
            messages: Current chat history, unused by this fixture.
            timeout: Request deadline, unused by this fixture.

        Returns:
            Scripted text and fixture provenance.

        Raises:
            RuntimeError: Responses were exhausted.
        """
        try:
            return next(self.responses), {
                "source": "fixture",
                "model_calls": 0,
            }
        except StopIteration as exc:
            raise RuntimeError(
                "Fixture exhausted before episode finished"
            ) from exc


class EndpointModel:
    """Call a configured OpenAI-compatible endpoint, once per turn."""

    def __init__(
        self,
        base_url: str,
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.6,
    ) -> None:
        """Configure one explicit endpoint.

        Args:
            base_url: OpenAI-compatible API base URL, including /v1 if needed.
            model: Served model name.
            max_tokens: Maximum response tokens.
            temperature: Sampling temperature.

        Raises:
            ValueError: URL is invalid or sends credentials over remote HTTP.
        """
        parsed = urllib.parse.urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Endpoint must be an HTTP(S) URL without credentials, query, or fragment"
            )
        if parsed.scheme == "http" and parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Non-local endpoints require HTTPS")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def complete(
        self, messages: list[dict[str, str]], timeout: float
    ) -> tuple[str, dict[str, Any]]:
        """Make one request and retain only content and numeric token usage.

        Args:
            messages: Chat history to send.
            timeout: Wall-clock deadline enforced by the parent process.

        Returns:
            Assistant text and token counts.

        Raises:
            TimeoutError: The transport worker exceeded its deadline.
            RuntimeError: The worker or HTTP request failed.
            ValueError: The response has no text content.
        """
        request = {
            "url": self.url,
            "body": {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "n": 1,
            },
            "timeout": timeout,
        }
        try:
            completed = subprocess.run(
                [sys.executable, str(ROOT / "http_client.py")],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(
                "Model request exceeded total deadline; request was not retried"
            ) from None
        if completed.returncode:
            raise RuntimeError(
                "Model transport worker failed; request was not retried"
            )
        envelope = json.loads(completed.stdout)
        if "error" in envelope:
            raise RuntimeError(envelope["error"])
        data = envelope["data"]
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("Model response has no text content")
        usage = {
            k: v
            for k, v in (data.get("usage") or {}).items()
            if k in {"prompt_tokens", "completion_tokens", "total_tokens"}
            and isinstance(v, int)
            and v >= 0
        }
        return content, usage
