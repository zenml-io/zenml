#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""What a host decides per call, and what the local server adds.

A host runs a tool with `ToolSpec.run` and a `ZenMLCall` that carries its
decisions: a secret page, a check before a sensitive write, read-only mode,
and a cache key per caller. The local server adds the start-up retry and
`zenml_report_feedback`.
"""

import asyncio
import json
from collections.abc import Sequence
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

pytest.importorskip("mcp")

from pydantic import ValidationError  # noqa: E402

from tests.unit.zenml_mcp.replay import connected  # noqa: E402
from zenml_mcp import server  # noqa: E402
from zenml_mcp.call import Asked, ZenMLCall  # noqa: E402
from zenml_mcp.client import (  # noqa: E402
    BearerToken,
    ZenMLRestClient,
    ZenMLUnavailable,
)
from zenml_mcp.registry import ToolSpec
from zenml_mcp.tools import TOOL_SPECS  # noqa: E402

PROJECT = "11111111-1111-4111-8111-111111111111"
SERVER_URL = "https://zenml.example"


def _spec(name: str) -> ToolSpec:
    return next(spec for spec in TOOL_SPECS if spec.name == name)


class _Page:
    """A secret page that records what it was asked for."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, dict[str, Any], Sequence[Asked]]] = []

    def awaiting_user(
        self, tool: str, arguments: dict[str, Any], asked: Sequence[Asked]
    ) -> dict[str, Any]:
        self.asked.append((tool, arguments, asked))
        return {"outcome": "awaiting_user", "url": "https://page.example/1"}


def _run(
    name: str,
    arguments: dict[str, Any],
    answer: Any = None,
    *,
    cache_key: str = "caller",
    token: str = "token-sample",
    **decisions: Any,
) -> tuple[Any, list[httpx.Request]]:
    """Run a tool as a host does and return its answer and the requests sent.

    Args:
        name: The tool.
        arguments: Its arguments.
        answer: Answers each request; by default ZenML is unreachable.
        cache_key: The caller's cache key.
        token: The caller's token.
        **decisions: The `ZenMLCall`'s host decisions.

    Returns:
        The tool's answer and every request it sent.
    """
    sent: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        if answer is None:
            raise httpx.ConnectError("unreachable")
        response: httpx.Response = answer(request)
        return response

    async def run() -> Any:
        transport = httpx.MockTransport(respond)
        async with httpx.AsyncClient(transport=transport) as http:
            client = ZenMLRestClient(
                SERVER_URL, BearerToken(token), http=http, cache_key=cache_key
            )
            call = ZenMLCall(client, **decisions)
            return await _spec(name).run(call, arguments)

    return asyncio.run(run()), sent


def test_a_secret_write_answers_with_the_page_and_sends_nothing() -> None:
    """With a secret page, a webhook's signing secret is typed there."""
    page = _Page()
    arguments = {
        "resource_type": "webhook",
        "project_id": PROJECT,
        "payload": {"name": "deploys", "webhook_type": "custom"},
    }
    answer, sent = _run("zenml_create_resource", arguments, secret_page=page)
    assert answer == {
        "outcome": "awaiting_user",
        "url": "https://page.example/1",
    }
    assert sent == []
    (tool, asked_with, asked) = page.asked[0]
    assert tool == "zenml_create_resource"
    assert asked_with["payload"] == arguments["payload"]
    assert [secret.path for secret in asked] == [("payload", "secret")]


def test_a_secret_in_the_call_is_refused_when_a_page_takes_it() -> None:
    """The model never carries a secret a page would ask the user for."""
    page = _Page()
    arguments = {
        "resource_type": "webhook",
        "project_id": PROJECT,
        "payload": {
            "name": "deploys",
            "webhook_type": "custom",
            "secret": "s3cr3t-test-value",
        },
    }
    answer, sent = _run("zenml_create_resource", arguments, secret_page=page)
    assert answer.is_error
    assert answer.structured_content["error"]["kind"] == "invalid_request"
    assert "s3cr3t-test-value" not in json.dumps(answer.structured_content)
    assert sent == [] and page.asked == []


class _Refused(Exception):
    """A host's refusal of a sensitive write."""


def _refuse(what: str) -> None:
    raise _Refused(what)


def test_a_stage_change_asks_the_host_before_anything_is_sent() -> None:
    """A host that refuses sensitive writes stops a stage change."""
    arguments = {
        "resource_type": "model_version",
        "resource_id": "0cc97e85-9562-4ba6-9ebf-ce23994051a0",
        "model_id": "0fa3bd0a-9114-4e91-b5aa-040057300b60",
        "project_id": PROJECT,
        "payload": {"stage": "staging"},
    }
    with pytest.raises(_Refused, match="model version's stage"):
        _run("zenml_update_resource", arguments, sensitive_write=_refuse)


def test_a_write_that_is_not_sensitive_does_not_ask_the_host() -> None:
    """Renaming a model version is no stage change."""
    seen: list[str] = []
    arguments = {
        "resource_type": "model_version",
        "resource_id": "0cc97e85-9562-4ba6-9ebf-ce23994051a0",
        "model_id": "0fa3bd0a-9114-4e91-b5aa-040057300b60",
        "project_id": PROJECT,
        "payload": {"name": "v2"},
    }
    _run("zenml_update_resource", arguments, sensitive_write=seen.append)
    assert seen == []


def test_the_catalog_follows_read_only_mode() -> None:
    """A read-only host's catalog offers no write operation."""
    writes = {"create", "update", "delete", "action"}
    arguments = {"resource_type": "pipeline"}
    offered, _ = _run("zenml_describe_resources", arguments)
    read_only, _ = _run("zenml_describe_resources", arguments, read_only=True)
    assert writes & set(offered["operations"])
    assert not writes & set(read_only["operations"])


def test_tools_that_read_no_server_are_marked_and_send_nothing() -> None:
    """A host may run them without a server or a sign-in."""
    serverless = {spec.name for spec in TOOL_SPECS if not spec.needs_server}
    assert serverless == {"zenml_describe_resources", "zenml_report_feedback"}
    _, sent = _run("zenml_describe_resources", {})
    assert sent == []


def test_every_tool_carries_its_read_only_hint() -> None:
    """A host derives access levels from the hints, so none may be unset."""
    assert all(
        spec.annotations.read_only_hint is not None for spec in TOOL_SPECS
    )
    assert all(
        spec.annotations.destructive_hint is not None
        for spec in TOOL_SPECS
        if not spec.annotations.read_only_hint
    )


def test_an_unknown_argument_is_refused() -> None:
    """A misspelled argument fails instead of being dropped."""
    with pytest.raises(ValidationError):
        _run("zenml_describe_resources", {"resource_kind": "pipeline"})


_PROJECTS = {
    "alice": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "bob": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
}


def _default_project_by_token(request: httpx.Request) -> httpx.Response:
    token = request.headers["Authorization"].removeprefix("Bearer ")
    if request.url.path == "/api/v1/current-user":
        return httpx.Response(
            200, json={"body": {"default_project_id": _PROJECTS[token]}}
        )
    page = {"index": 1, "max_size": 20, "total_pages": 1, "total": 0}
    return httpx.Response(200, json={**page, "items": []})


def test_callers_never_share_a_cached_default_project() -> None:
    """Each caller's own default project scopes its list, cache or not."""
    arguments = {"resource_type": "pipeline"}
    projects = []
    for token, key in (
        ("alice", "key-a"),
        ("bob", "key-b"),
        ("alice", "key-a"),
    ):
        _, sent = _run(
            "zenml_list_resources",
            arguments,
            _default_project_by_token,
            cache_key=key,
            token=token,
        )
        listed = next(r for r in sent if r.url.path == "/api/v1/pipelines")
        projects.append(parse_qs(urlsplit(str(listed.url)).query)["project"])
    alice, bob = [_PROJECTS["alice"]], [_PROJECTS["bob"]]
    assert projects == [alice, bob, alice]


def test_feedback_drafts_a_zenml_issue_and_cuts_a_long_one() -> None:
    """The link opens a pre-filled zenml-io/zenml issue of at most 8,000 chars."""
    short, sent = _run(
        "zenml_report_feedback",
        {
            "title": "A confusing error",
            "what_happened": "zenml_get_resource said nothing useful.",
            "proposed_fix": "Name the missing argument.",
            "tool_name": "zenml_get_resource",
        },
    )
    assert sent == []
    assert short["issue_url"].startswith(
        "https://github.com/zenml-io/zenml/issues/new?title="
    )
    assert short["truncated"] is False and "body" not in short
    long, _ = _run(
        "zenml_report_feedback",
        {
            "title": "A long report",
            "what_happened": "x" * 20_000,
            "proposed_fix": "Shorter errors.",
        },
    )
    assert long["truncated"] is True
    assert len(long["issue_url"]) <= 8000
    assert "x" * 20_000 in long["body"]


def test_feedback_refuses_an_empty_field() -> None:
    """A report needs a title, what happened and a proposed fix."""
    refused, _ = _run(
        "zenml_report_feedback",
        {"title": " ", "what_happened": "x", "proposed_fix": "y"},
    )
    assert refused.structured_content["error"]["kind"] == "invalid_request"


def _start(
    answers: list[Any], monkeypatch: pytest.MonkeyPatch
) -> tuple[Any, list[httpx.Request]]:
    """Check a server whose `/info` answers come from `answers`, in order.

    Args:
        answers: An exception to raise or a status to answer, per request.
        monkeypatch: Removes the retry's wait.

    Returns:
        The check's answer or exception, and the requests sent.
    """
    monkeypatch.setattr(server, "START_RETRY_DELAY_S", 0.0)
    sent: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return httpx.Response(answer, json={"version": "0.99.0"})

    async def check() -> Any:
        transport = httpx.MockTransport(respond)
        async with httpx.AsyncClient(transport=transport) as http:
            client = ZenMLRestClient(
                SERVER_URL, BearerToken("t"), http=http, cache_key="k"
            )
            try:
                return await server.check_server(client)
            except ZenMLUnavailable as error:
                return error

    return asyncio.run(check()), sent


def test_start_up_retries_once_after_a_network_stall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mcp-zenml #96: one retry when the server can't be reached."""
    info, sent = _start([httpx.ConnectError("stall"), 200], monkeypatch)
    assert info == {"version": "0.99.0"} and len(sent) == 2
    failed, sent = _start(
        [httpx.ConnectError("stall"), httpx.ConnectError("stall")], monkeypatch
    )
    assert isinstance(failed, ZenMLUnavailable) and len(sent) == 2


def test_start_up_does_not_retry_a_server_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A server that answered is not stalled: its error stands."""
    failed, sent = _start([503], monkeypatch)
    assert isinstance(failed, ZenMLUnavailable) and len(sent) == 1


def _unreachable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("unreachable")


def test_the_local_server_refuses_an_unknown_argument() -> None:
    """A misspelled argument fails over MCP too, and nothing is sent."""

    async def call() -> Any:
        async with connected(_unreachable) as mcp:
            listed = await mcp.list_tools()
            schema = next(
                t.input_schema
                for t in listed.tools
                if t.name == "zenml_list_resources"
            )
            result = await mcp.call_tool(
                "zenml_list_resources",
                {"resource_type": "pipeline", "filter": {"name": "x"}},
            )
            return schema, result

    schema, result = asyncio.run(call())
    assert schema["additionalProperties"] is False
    assert result.is_error


@pytest.mark.parametrize(
    "uri",
    [
        "ui://zenml/apps/pipeline-runs/index.html",
        "ui://zenml/apps/run-activity-chart/index.html",
    ],
)
def test_a_view_loads_nothing_from_another_origin(uri: str) -> None:
    """Each view inlines its App library and calls with what opened it.

    Args:
        uri: The view's resource.
    """

    async def read() -> str:
        async with connected(_unreachable) as mcp:
            view = await mcp.read_resource(uri)
            return view.contents[0].text  # type: ignore[union-attr]

    html = asyncio.run(read())
    assert "unpkg.com" not in html
    assert "const { App } = (() => {" in html
    assert "callOpenedIn(toolName, args)" in html
    assert "app.ontoolinput" in html
