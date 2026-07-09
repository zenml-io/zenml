"""HTTP client for remote-serving rollout generation."""

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple


class VLLMEndpointError(RuntimeError):
    """The version's vLLM endpoint could not be reached."""


def post_chat_completions(
    *,
    endpoint_url: str,
    adapter_name: str,
    messages: List[Dict[str, str]],
    group_size: int,
    temperature: float,
    max_tokens: int,
    timeout: int = 600,
) -> List[Dict[str, Any]]:
    """Request group_size completions for one prompt from the vLLM server.

    Args:
        endpoint_url: Base URL of the version's vLLM server.
        adapter_name: LoRA adapter name loaded into that server.
        messages: Chat messages for one task.
        group_size: Number of sampled completions to request.
        temperature: Sampling temperature.
        max_tokens: Generation cap.
        timeout: Per-request timeout.

    Raises:
        VLLMEndpointError: If the server is unreachable (e.g. torn down).
        ValueError: If the server returns the wrong number of choices.

    Returns:
        The OpenAI chat completion choices.
    """
    url = f"{endpoint_url.rstrip('/')}/v1/chat/completions"
    request = urllib.request.Request(
        url,
        data=json.dumps(
            {
                "model": adapter_name,
                "messages": messages,
                "n": group_size,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "logprobs": True,
                # vLLM extension: encode logprob tokens as "token_id:<n>" so
                # completion IDs come from the same array as the logprobs.
                "return_tokens_as_token_ids": True,
                "chat_template_kwargs": {"enable_thinking": False},
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode())
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        raise VLLMEndpointError(
            f"vLLM endpoint {endpoint_url!r} is unreachable: {e}"
        ) from e
    choices = body.get("choices") or []
    if len(choices) != group_size:
        raise ValueError(
            f"vLLM returned {len(choices)} choices, expected {group_size}."
        )
    return choices


def extract_ids_and_logprobs(
    choice: Dict[str, Any],
) -> Tuple[List[int], List[float]]:
    """Extract sampled token IDs and logprobs from one completion choice.

    Requires `return_tokens_as_token_ids`, which encodes each logprob
    entry's token as "token_id:<int>". Taking the IDs from the same array
    as the logprobs keeps the two aligned by construction. Re-tokenizing
    the completion text undercounts by one, because the stop token carries
    a logprob but is not part of the returned text.

    Args:
        choice: One OpenAI chat completion choice from vLLM.

    Raises:
        ValueError: If the response lacks token-ID-encoded logprobs.

    Returns:
        Parallel lists of sampled token IDs and their logprobs.
    """
    content = (choice.get("logprobs") or {}).get("content") or []
    ids: List[int] = []
    logprobs: List[float] = []
    for entry in content:
        token = entry.get("token") or ""
        logprob = entry.get("logprob")
        if logprob is None or not token.startswith("token_id:"):
            raise ValueError(
                "vLLM HTTP response did not include token-ID-encoded "
                f"sampled-token logprobs (got token={token!r}). Remote "
                "serving needs `return_tokens_as_token_ids`."
            )
        ids.append(int(token.split(":", 1)[1]))
        logprobs.append(float(logprob))
    if not ids:
        raise ValueError(
            "vLLM HTTP response contained no sampled-token logprobs."
        )
    return ids, logprobs


def completion_text(choice: Dict[str, Any]) -> str:
    """Return the assistant text from one OpenAI chat completion choice.

    Args:
        choice: One OpenAI chat completion choice from vLLM.

    Raises:
        ValueError: If the choice has no string message content.

    Returns:
        The assistant message text.
    """
    message = choice.get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError(f"Unexpected vLLM chat completion choice: {choice}")
    return content
