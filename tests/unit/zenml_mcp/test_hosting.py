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
import copy
import json
import logging
import shutil
import subprocess
from collections.abc import Sequence
from typing import Any, Optional
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

pytest.importorskip("mcp")

from pydantic import ValidationError  # noqa: E402

from tests.unit.zenml_mcp.replay import connected, golden  # noqa: E402
from zenml_mcp import server, views  # noqa: E402
from zenml_mcp.call import Asked, ZenMLCall  # noqa: E402
from zenml_mcp.client import (  # noqa: E402
    BearerToken,
    ZenMLAuth,
    ZenMLAuthError,
    ZenMLRestClient,
    ZenMLUnavailable,
)
from zenml_mcp.registry import ToolSpec
from zenml_mcp.resource_catalog import RESOURCE_REGISTRY  # noqa: E402
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
    project: Optional[str] = None,
    **decisions: Any,
) -> tuple[Any, list[httpx.Request]]:
    """Run a tool as a host does and return its answer and the requests sent.

    Args:
        name: The tool.
        arguments: Its arguments.
        answer: Answers each request; by default ZenML is unreachable.
        cache_key: The caller's cache key.
        token: The caller's token.
        project: The client's project for calls that name none.
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
                SERVER_URL,
                BearerToken(token),
                http=http,
                cache_key=cache_key,
                project=project,
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


_TRIGGER = "5824096b-e808-40aa-8d4e-44d7249b4499"
_SNAPSHOT = "4c5dd2b9-c31a-42da-a776-418993f24a6e"


@pytest.mark.parametrize(
    ("tool", "arguments", "what"),
    [
        (
            "zenml_action_resource",
            {
                "resource_type": "pipeline_run",
                "action": "replay",
                "resource_id": "c6a6047f-0c8d-4950-9a7a-d51093e4321b",
                "project_id": PROJECT,
            },
            "Replaying a pipeline run",
        ),
        (
            "zenml_action_resource",
            {
                "resource_type": "schedule_trigger",
                "action": "attach",
                "resource_id": _TRIGGER,
                "project_id": PROJECT,
                "payload": {"snapshot_id": _SNAPSHOT},
            },
            "Attaching a schedule trigger to a snapshot",
        ),
        (
            "zenml_update_resource",
            {
                "resource_type": "schedule_trigger",
                "resource_id": _TRIGGER,
                "project_id": PROJECT,
                "payload": {"active": True},
            },
            "Changing a schedule trigger",
        ),
        (
            "zenml_update_resource",
            {
                "resource_type": "webhook",
                "resource_id": "a57684e2-c51e-4278-be08-ff69b9c0ea4a",
                "project_id": PROJECT,
                "payload": {"active": True},
            },
            "Switching a webhook on",
        ),
    ],
)
def test_a_write_that_can_start_runs_asks_the_host_first(
    tool: str, arguments: dict[str, Any], what: str
) -> None:
    """A host that refuses run-starting writes stops them before any request.

    Args:
        tool: The generic write tool.
        arguments: A write that starts runs or arms a trigger.
        what: What the host is told the write does.
    """
    sent: list[httpx.Request] = []

    def unreachable(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        raise httpx.ConnectError("unreachable")

    with pytest.raises(_Refused) as refused:
        _run(tool, arguments, unreachable, sensitive_write=_refuse)
    assert str(refused.value) == what
    assert sent == []


def test_every_write_that_can_start_runs_is_declared_sensitive() -> None:
    """A trigger type added to the catalog is gated without being listed."""
    triggers = [
        spec
        for spec in RESOURCE_REGISTRY.values()
        if spec.rest.route == "/triggers"
    ]
    assert triggers
    for spec in triggers:
        assert all(m.sensitive for m in spec.mutations.values()), spec
        assert spec.actions["attach"].sensitive, spec
    assert RESOURCE_REGISTRY["pipeline_run"].actions["replay"].sensitive
    # A webhook's triggers dispatch runs only while it is on.
    webhook = RESOURCE_REGISTRY["webhook"].mutations["update"].sensitive
    assert webhook is not None and webhook.when_set == ("active",)


def test_a_read_only_call_refuses_a_write_tool_before_sending() -> None:
    """`ToolSpec.run` refuses writes itself, whatever tools a host lists."""
    arguments = {
        "resource_type": "tag",
        "payload": {"name": "reviewed"},
    }
    answer, sent = _run("zenml_create_resource", arguments, read_only=True)
    assert answer.is_error
    assert answer.structured_content["error"]["kind"] == "permission_denied"
    assert sent == []


def test_a_read_only_server_lists_no_write_tool() -> None:
    """What `zenml mcp --read-only` builds offers only the read tools."""

    async def listed() -> set[str]:
        async with connected(_unreachable, read_only=True) as mcp:
            return {tool.name for tool in (await mcp.list_tools()).tools}

    reads = {
        spec.name for spec in TOOL_SPECS if spec.annotations.read_only_hint
    }
    assert asyncio.run(listed()) == reads


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


def test_a_client_project_scopes_the_calls_that_name_none() -> None:
    """The project `zenml project set` chose wins over the server's default."""
    _, sent = _run(
        "zenml_list_resources",
        {"resource_type": "pipeline"},
        _default_project_by_token,
        cache_key="key-chosen",
        token="alice",
        project=_PROJECTS["bob"],
    )
    listed = next(r for r in sent if r.url.path == "/api/v1/pipelines")
    query = parse_qs(urlsplit(str(listed.url)).query)
    assert query["project"] == [_PROJECTS["bob"]]
    assert all(r.url.path != "/api/v1/current-user" for r in sent)


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
    answers: list[Any], monkeypatch: pytest.MonkeyPatch, user: int = 200
) -> tuple[Any, list[httpx.Request]]:
    """Check a server whose `/info` answers come from `answers`, in order.

    Args:
        answers: An exception to raise or a status to answer, per request.
        monkeypatch: Removes the retry's wait.
        user: The status `/current-user` answers with.

    Returns:
        The check's answer or exception, and the `/info` requests sent.
    """
    monkeypatch.setattr(server, "START_RETRY_DELAY_S", 0.0)
    sent: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/current-user":
            return httpx.Response(user, json={"detail": "revoked"})
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
            except (ZenMLUnavailable, ZenMLAuthError) as error:
                return error

    return asyncio.run(check()), sent


def test_start_up_refuses_a_token_the_server_no_longer_accepts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`/info` needs no sign-in, so the check reads the signed-in user too."""
    refused, _ = _start([200], monkeypatch, user=401)
    assert isinstance(refused, ZenMLAuthError)


def test_start_up_retries_once_after_a_network_stall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """zenml-io/mcp-zenml#96: one retry when the server can't be reached."""
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


# A list of 15 items read 20 at a time, where a page of 20 doesn't fit in one
# answer and is cut to 5: as `zenml_list_resources` answers.
_PAGED_LIST = r"""
const items = Array.from({ length: 15 }, (_, i) => ({ id: i }));
const asked = [];
async function callServerToolSafe(name, args) {
  asked.push([args.page, args.size]);
  const start = (args.page - 1) * args.size;
  if (start >= items.length) {
    return { error: { kind: "invalid_request", message: "page out of range" } };
  }
  const page = items.slice(start, start + args.size);
  if (args.size === 20) {
    return { items: page.slice(0, 5), total: 15, page: 1, size: 20,
             truncated: true, next: { size: 5, page: 2 } };
  }
  return { items: page, total: 15, page: args.page, size: args.size };
}
listPage({ resource_type: "pipeline_run", page: 1, size: 20 }).then(
  (result) => console.log(JSON.stringify({ result, asked })),
);
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js")
def test_a_view_reads_no_page_past_the_last_item() -> None:
    """A short last page ends the read; ZenML refuses a page past the end."""
    script = views._LIST_PAGE + _PAGED_LIST
    out = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    read = json.loads(out.stdout)
    assert [item["id"] for item in read["result"]["items"]] == list(range(15))
    assert read["asked"] == [[1, 20], [2, 5], [3, 5]]


def test_a_connector_update_keeps_its_stored_secrets_out_of_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Without a secret page too, a resent stored secret never comes back.

    An update without `configuration` resends the stored secrets, as
    upstream does; a refusal that echoes one shows it to neither the model
    nor the log.
    """
    caplog.set_level(logging.DEBUG)
    connector = copy.deepcopy(
        golden("generic_write.json")["entities"]["service_connector"]
    )
    stored = "-".join(("stored", "never", "shown"))
    connector["metadata"]["configuration"]["password"] = stored
    resent: list[Any] = []

    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.path != f"/api/v1/service_connectors/{connector['id']}":
            return httpx.Response(404, json={"detail": "Not Found"})
        if request.method == "GET":
            return httpx.Response(200, json=connector)
        resent.append(json.loads(request.content))
        detail = ["ValueError", f"Rejected {stored}"]
        return httpx.Response(400, json={"detail": detail})

    refused, _ = _run(
        "zenml_update_resource",
        {
            "resource_type": "service_connector",
            "resource_id": connector["id"],
            "payload": {"description": "d"},
        },
        answer,
    )
    assert resent and resent[0]["configuration"]["password"] == stored
    assert refused.structured_content["error"]["kind"] == "invalid_request"
    assert stored not in json.dumps(refused.structured_content)
    assert stored not in caplog.text


class _Counted(ZenMLAuth):
    """No token, for a server without authentication; counts the asks."""

    def __init__(self) -> None:
        super().__init__()
        self.asked = 0

    async def token(self) -> Optional[str]:
        self.asked += 1
        return None

    async def renew(self, rejected: Optional[str]) -> str:
        raise ZenMLUnavailable("not expected")


def test_an_unsigned_client_asks_for_a_token_once() -> None:
    """A None token is kept like any other, not asked for per request."""
    auth = _Counted()

    async def read() -> None:
        transport = httpx.MockTransport(lambda _: httpx.Response(200, json={}))
        async with httpx.AsyncClient(transport=transport) as http:
            client = ZenMLRestClient(
                SERVER_URL, auth, http=http, cache_key="k"
            )
            for _ in range(3):
                await client.get("/info", what="Reading")

    asyncio.run(read())
    assert auth.asked == 1


def test_feedback_masks_a_credential_in_the_public_issue() -> None:
    """A token the model quoted doesn't reach the drafted public issue."""
    drafted, _ = _run(
        "zenml_report_feedback",
        {
            "title": "Login fails",
            "what_happened": "Sent Authorization: Bearer zenkey_s3cr3tvalue",
            "proposed_fix": "Explain the refusal.",
        },
    )
    assert "s3cr3tvalue" not in drafted["issue_url"]


def test_a_stored_secret_cut_by_the_message_limit_is_masked_too(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A long refusal that cuts the echoed secret shows none of it."""
    connector = copy.deepcopy(
        golden("generic_write.json")["entities"]["service_connector"]
    )
    stored = "-".join(("stored", "never", "shown", "at", "all"))
    connector["metadata"]["configuration"]["password"] = stored

    def answer(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=connector)
        # ZenML's detail is cut at 500 characters, inside the secret.
        detail = ["ValueError", "x" * 470 + stored]
        return httpx.Response(400, json={"detail": detail})

    refused, _ = _run(
        "zenml_update_resource",
        {
            "resource_type": "service_connector",
            "resource_id": connector["id"],
            "payload": {"description": "d"},
        },
        answer,
    )
    message = refused.structured_content["error"]["message"]
    assert stored[:8] not in message


def test_feedback_masks_a_title_before_cutting_it() -> None:
    """A credential the length limit would cut is still masked."""
    title = "t" * 180 + " https://user:pa55wordlong@host.example"
    drafted, _ = _run(
        "zenml_report_feedback",
        {"title": title, "what_happened": "x", "proposed_fix": "y"},
    )
    query = parse_qs(urlsplit(drafted["issue_url"]).query)
    assert "pa5" not in query["title"][0]


class _FailedSignIn(ZenMLAuth):
    """A sign-in the server answered with an error."""

    def __init__(self) -> None:
        super().__init__()
        self.asked = 0

    async def token(self) -> Optional[str]:
        self.asked += 1
        raise ZenMLUnavailable("Signing in to ZenML failed (RuntimeError).")

    async def renew(self, rejected: Optional[str]) -> str:
        raise ZenMLUnavailable("not expected")


def test_start_up_does_not_retry_a_failed_sign_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only a request that got no answer is a stall worth retrying."""
    monkeypatch.setattr(server, "START_RETRY_DELAY_S", 0.0)
    auth = _FailedSignIn()

    async def check() -> None:
        transport = httpx.MockTransport(
            lambda _: httpx.Response(200, json={"version": "0.99.0"})
        )
        async with httpx.AsyncClient(transport=transport) as http:
            client = ZenMLRestClient(
                SERVER_URL, auth, http=http, cache_key="k"
            )
            with pytest.raises(ZenMLUnavailable):
                await server.check_server(client)

    asyncio.run(check())
    assert auth.asked == 1


class _Rotating(ZenMLAuth):
    """Each renewal of a token gives the next one."""

    async def token(self) -> Optional[str]:
        return "T1"

    async def renew(self, rejected: Optional[str]) -> str:
        return {"T1": "T2", "T2": "T3"}[str(rejected)]


def test_a_late_refusal_of_an_old_token_keeps_the_newer_one() -> None:
    """A request refused on T1 after others moved to T3 doesn't bring T2 back."""
    auth = _Rotating()
    refused = httpx.Response(401)

    async def run() -> str:
        late = auth.async_auth_flow(httpx.Request("GET", SERVER_URL))
        await late.__anext__()
        for _ in range(2):
            flow = auth.async_auth_flow(httpx.Request("GET", SERVER_URL))
            await flow.__anext__()
            await flow.asend(refused)
        await late.asend(refused)
        after = auth.async_auth_flow(httpx.Request("GET", SERVER_URL))
        sent = await after.__anext__()
        return sent.headers["Authorization"]

    assert asyncio.run(run()) == "Bearer T3"


def test_a_renewal_that_returns_a_refused_token_renews_again() -> None:
    """A late refusal of T1 after T2 was refused moves on to T3."""
    auth = _Rotating()
    refused = httpx.Response(401)

    async def run() -> str:
        late = auth.async_auth_flow(httpx.Request("GET", SERVER_URL))
        await late.__anext__()
        first = auth.async_auth_flow(httpx.Request("GET", SERVER_URL))
        await first.__anext__()
        await first.asend(refused)
        with pytest.raises(StopAsyncIteration):
            await first.asend(refused)
        retried = await late.asend(refused)
        return retried.headers["Authorization"]

    assert asyncio.run(run()) == "Bearer T3"


def test_a_pipeline_without_runs_is_described_with_none() -> None:
    """No runs: an empty history, no latest run, nothing read per run."""
    pipeline = copy.deepcopy(
        golden("generic_read.json")["entities"]["pipeline"]
    )

    def answer(request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/api/v1")
        if path == f"/pipelines/{pipeline['id']}":
            return httpx.Response(200, json=pipeline)
        if path in {"/runs", "/pipeline_snapshots"}:
            page = {"index": 1, "max_size": 20, "total_pages": 1, "total": 0}
            return httpx.Response(200, json={**page, "items": []})
        if path == "/info":
            return httpx.Response(200, json={"version": "0.99.0"})
        if path.startswith("/projects/"):
            return httpx.Response(200, json={"name": "default"})
        return httpx.Response(404, json={"detail": "Not Found"})

    described, _ = _run(
        "zenml_get_pipeline", {"pipeline": pipeline["id"]}, answer
    )
    assert described["runs"] == []
    assert described["latest_run"] is None
    assert described["step_health_runs"] == 0
