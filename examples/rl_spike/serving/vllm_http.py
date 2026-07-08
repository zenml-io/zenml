"""HTTP client for warm-vLLM rollout generation."""

import json
import urllib.request
from typing import Any, Dict, List

from generation import EPISODE_KEYS


def _post_json(
    url: str, payload: Dict[str, Any], timeout: int = 600
) -> Dict[str, Any]:
    """POST JSON to the vLLM OpenAI-compatible API."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def _extract_ids_and_logprobs(
    choice: Dict[str, Any],
) -> "tuple[List[int], List[float]]":
    """Extract sampled token IDs and logprobs from one completion choice.

    Requires the request to set `return_tokens_as_token_ids`, which makes
    vLLM encode each logprob entry's token as "token_id:<int>". Taking the
    IDs from the same array as the logprobs makes the two aligned by
    construction — re-tokenizing the completion *text* undercounts by one
    because the stop token (`<|im_end|>`) is generated (and carries a
    logprob) but is not part of the returned text (hit live: 57 logprobs
    vs 56 re-tokenized IDs).

    Args:
        choice: One OpenAI chat completion choice from vLLM.

    Returns:
        Parallel lists of sampled token IDs and their logprobs.

    Raises:
        ValueError: If the response lacks token-ID-encoded logprobs.
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
                f"sampled-token logprobs (got token={token!r}). The "
                "warm-vLLM mode needs `return_tokens_as_token_ids`."
            )
        ids.append(int(token.split(":", 1)[1]))
        logprobs.append(float(logprob))
    if not ids:
        raise ValueError(
            "vLLM HTTP response contained no sampled-token logprobs. "
            "The warm-vLLM mode needs per-token logprobs for TRL."
        )
    return ids, logprobs


def _completion_text(choice: Dict[str, Any]) -> str:
    """Return the assistant text from one OpenAI chat completion choice."""
    message = choice.get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError(f"Unexpected vLLM chat completion choice: {choice}")
    return content


def generate_vllm_chat_completions(
    *,
    endpoint_url: str,
    model_name: str,
    adapter_name: str,
    tasks: List[Dict[str, Any]],
    group_size: int,
    temperature: float = 0.9,
    max_tokens: int = 1024,
    timeout: int = 600,
) -> List[Dict[str, Any]]:
    """Generate rollout records through a warm vLLM OpenAI endpoint.

    Args:
        endpoint_url: Base URL of the vLLM OpenAI server.
        model_name: HF model ID, used only to load the matching tokenizer.
        adapter_name: Runtime LoRA adapter name already loaded into vLLM.
        tasks: Task records from tasks.jsonl.
        group_size: Number of sampled completions per task.
        temperature: Sampling temperature.
        max_tokens: Generation cap.
        timeout: Per-request timeout.

    Returns:
        One episode dict per (task, rollout_index), matching
        generation.EPISODE_KEYS.

    Raises:
        ValueError: If the HTTP logprobs do not align with tokenizer IDs.
    """
    from prompts import build_prompt, strip_markdown_fences
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    episodes = []
    completions_url = f"{endpoint_url.rstrip('/')}/v1/chat/completions"
    for task in tasks:
        messages = build_prompt(task["prompt"])
        # Two explicit calls instead of one apply_chat_template: its
        # return type shifts across transformers versions, and a str
        # slipping through becomes list-of-characters prompt_ids that
        # crash TRL with "too many dimensions 'str'" (hit live).
        prompt_text = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )
        prompt_ids = tokenizer(prompt_text, add_special_tokens=False).input_ids
        response = _post_json(
            completions_url,
            {
                "model": adapter_name,
                "messages": messages,
                "n": group_size,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "logprobs": True,
                # vLLM extension: encode logprob tokens as "token_id:<n>"
                # so completion IDs come from the same array as logprobs.
                "return_tokens_as_token_ids": True,
            },
            timeout=timeout,
        )
        choices = response.get("choices") or []
        if len(choices) != group_size:
            raise ValueError(
                f"vLLM returned {len(choices)} choices for task {task['id']}, "
                f"expected {group_size}."
            )
        for rollout_index, choice in enumerate(choices):
            completion_text = _completion_text(choice)
            completion_ids, logprobs = _extract_ids_and_logprobs(choice)
            episodes.append(
                {
                    "task_id": task["id"],
                    "rollout_index": rollout_index,
                    "prompt_text": prompt_text,
                    "completion_text": completion_text,
                    "program_text": strip_markdown_fences(completion_text),
                    "prompt_ids": list(prompt_ids),
                    "completion_ids": completion_ids,
                    "logprobs": logprobs,
                    "spec": task["spec"],
                }
            )
    for episode in episodes:
        missing = set(EPISODE_KEYS) - set(episode)
        if missing:
            raise ValueError(
                f"HTTP generator emitted an episode missing keys {missing} "
                f"(task {episode.get('task_id')})."
            )
    return episodes
