"""Offline request and fallback checks for the agent examples."""

import importlib.util
import json
import sys
from collections.abc import Callable, Iterator
from functools import partial
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import Mock

import pytest


@pytest.fixture(params=["agent_comparison", "agent_outer_loop"])
def llm_call(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[Callable[[], str], list[dict[str, Any]], dict[str, bool]]]:
    """Import each helper and route its real SDK requests to a local transport.

    Args:
        request: The example selected by pytest.
        monkeypatch: Scoped environment and client replacements.

    Yields:
        A helper invocation, recorded requests, and response controls.
    """
    httpx = pytest.importorskip("httpx")
    openai = pytest.importorskip("openai")
    for key in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "COHERE_API_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-key")
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")

    requests: list[dict[str, Any]] = []
    controls = {"empty": False}

    def respond(http_request: Any) -> Any:
        body = json.loads(http_request.content)
        requests.append(body)
        # A small reasoning budget can be exhausted before visible output.
        reasoning_tokens = 0 if body.get("reasoning_effort") == "none" else 256
        exhausted = body["max_completion_tokens"] <= reasoning_tokens
        empty = controls["empty"] or exhausted
        return httpx.Response(
            200,
            json={
                "id": "offline-completion",
                "object": "chat.completion",
                "created": 1,
                "model": body["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": ""
                            if empty
                            else "Freeze your card in the app.",
                        },
                        "finish_reason": "length" if empty else "stop",
                    }
                ],
            },
        )

    example_dir = Path(__file__).parents[3] / "examples" / request.param

    def load_module(name: str, path: Path) -> ModuleType:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        client = openai.OpenAI(
            api_key="offline-test-key", http_client=http_client, max_retries=0
        )
        if request.param == "agent_comparison":
            litellm = pytest.importorskip("litellm")
            module = load_module(
                "comparison_llm_utils", example_dir / "llm_utils.py"
            )
            completion = litellm.completion

            def local_completion(**kwargs: Any) -> Any:
                return completion(**kwargs, client=client)

            monkeypatch.setattr(litellm, "completion", local_completion)
            call = partial(module.call_llm, "I lost my card.")
        else:
            prompts = load_module("prompts", example_dir / "prompts.py")
            monkeypatch.setitem(sys.modules, "prompts", prompts)
            module = load_module("outer_loop_utils", example_dir / "utils.py")
            monkeypatch.setattr(module, "OpenAI", lambda **kwargs: client)
            call = partial(
                module.generate_llm_response, "I lost my card.", "card_lost"
            )
        yield call, requests, controls


def test_response_survives_completion_budget(llm_call: Any) -> None:
    """Return the model answer rather than exhausting the budget on reasoning.

    Args:
        llm_call: The helper and local completion transport.
    """
    call, requests, _ = llm_call

    assert call() == "Freeze your card in the app."
    assert requests[0]["model"] == "gpt-5.6-luna"
    assert requests[0]["reasoning_effort"] == "none"


def test_missing_key_uses_fallback_without_request(
    llm_call: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the examples usable offline without issuing an SDK request.

    Args:
        llm_call: The helper and local completion transport.
        monkeypatch: Scoped environment replacements.
    """
    call, requests, _ = llm_call
    monkeypatch.delenv("OPENAI_API_KEY")

    assert call() != "Freeze your card in the app."
    assert requests == []


def test_empty_length_limited_completion_uses_fallback(llm_call: Any) -> None:
    """Do not present an empty completion as an LLM-generated answer.

    Args:
        llm_call: The helper and local completion transport.
    """
    call, requests, controls = llm_call
    controls["empty"] = True

    response = call()

    assert response
    assert response != "Freeze your card in the app."
    assert len(requests) == 1


@pytest.mark.parametrize("llm_call", ["agent_comparison"], indirect=True)
def test_alternative_model_keeps_provider_parameters(
    llm_call: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not send Luna reasoning controls to an explicitly selected provider.

    Args:
        llm_call: The helper and local completion transport.
        monkeypatch: Scoped SDK replacements.
    """
    call, _, _ = llm_call
    litellm = sys.modules["litellm"]
    completion = Mock(
        return_value=litellm.ModelResponse(
            choices=[{"message": {"content": "Alternative provider answer."}}]
        )
    )
    monkeypatch.setattr(litellm, "completion", completion)

    assert (
        call(model="anthropic/claude-3-haiku")
        == "Alternative provider answer."
    )
    assert completion.call_args.kwargs["model"] == "anthropic/claude-3-haiku"
    assert "reasoning_effort" not in completion.call_args.kwargs
