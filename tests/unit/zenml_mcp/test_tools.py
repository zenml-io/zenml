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
"""How the ZenML MCP tools answer, refuse and page, against a fake ZenML.

Answer size caps, step-log paging and cursors, line-ranged step code, error
kinds and messages, credential masking, and refusals before anything reaches
ZenML.
"""

import asyncio
import base64
import json
import uuid
from collections.abc import Awaitable, Callable, Sequence
from inspect import isawaitable
from typing import Any, Optional, Union

import httpx
import pytest

pytest.importorskip("mcp")

from tests.unit.zenml_mcp.replay import (  # noqa: E402
    connected,
    golden,
    result_of,
)
from zenml_mcp.call import ZenMLCall  # noqa: E402
from zenml_mcp.client import (  # noqa: E402
    ZenMLAuth,
    ZenMLAuthError,
    ZenMLRestClient,
)
from zenml_mcp.common import encoded_size  # noqa: E402
from zenml_mcp.credentials import (  # noqa: E402
    credential_like_keys,
    redact,
)

GOLDEN = golden("generic_read.json")
WRITE_GOLDEN = golden("generic_write.json")

USER_ID = "33333333-3333-4333-8333-333333333333"
PROJECT_IDS = (
    "44444444-4444-4444-8444-444444444444",
    "55555555-5555-4555-8555-555555555555",
)

Reply = Union[httpx.Response, Awaitable[httpx.Response]]
Route = Callable[[httpx.Request], Reply]


def _json(body: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=body)


class _ZenML:
    """A fake ZenML server that records what reached it.

    It answers `/current-user` with the default project `p1` and `/info`
    as a ZenML server does, each path in `answers` with its route, and any
    other path with a 599, so a request no test expected stands out.
    """

    def __init__(self, answers: Optional[dict[str, Route]] = None) -> None:
        self.answers = answers or {}
        self.seen: list[dict[str, Any]] = []
        self.unscripted: list[str] = []

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        params = request.url.params
        sent: dict[str, Any] = {
            "method": request.method,
            "path": request.url.path,
            "params": {key: params.get_list(key) for key in params.keys()},
        }
        if request.content:
            try:
                sent["body"] = json.loads(request.content)
            except ValueError:
                sent["body"] = request.content.decode(errors="replace")
        self.seen.append(sent)
        if request.url.path in self.answers:
            answered = self.answers[request.url.path](request)
            return await answered if isawaitable(answered) else answered
        if request.url.path == "/api/v1/current-user":
            body = {"default_project_id": "p1"}
            return _json({"id": "u1", "name": "u1", "body": body})
        if request.url.path == "/api/v1/info":
            return _json({"version": "0.98.0", "deployment_type": "cloud"})
        self.unscripted.append(request.url.path)
        return _json({"detail": "unscripted"}, 599)


def _never_echoed() -> str:
    # Built at run time: a literal next to these key names trips secret
    # scanners.
    return "-".join(("never", "echoed"))


def _error(result: Any) -> dict[str, Any]:
    error: dict[str, Any] = result.structured_content["error"]
    return error


def test_a_generic_write_is_refused_before_anything_reaches_zenml() -> None:
    """Credential-like keys, writes not offered and ids that leave the route.

    A webhook's own `secret` is not refused here: without a secret page it
    is sent, as `test_replay.py` checks.
    """
    value = _never_echoed()
    project = {"project_id": GOLDEN["project"]}
    component = {
        "name": "c",
        "flavor": "aws",
        "component_type": "orchestrator",
    }
    hook = {"name": "h", "webhook_id": USER_ID}
    refusals: list[tuple[str, str, dict[str, Any]]] = [
        (
            "aws_secret_access_key",
            "create",
            {
                "resource_type": "stack_component",
                "payload": {
                    **component,
                    "configuration": {"aws_secret_access_key": value},
                },
            },
        ),
        (
            "token",
            "update",
            {
                "resource_type": "code_repository",
                "resource_id": USER_ID,
                "payload": {"config": {"token": value}},
                **project,
            },
        ),
        (
            "api_key",
            "create",
            {
                "resource_type": "webhook_trigger",
                "payload": {
                    **hook,
                    "configuration": {"on": [{"api_key": value}]},
                },
                **project,
            },
        ),
        (
            "does not offer",
            "delete",
            {"resource_type": "deployment", "resource_id": USER_ID, **project},
        ),
        (
            "exact UUID",
            "delete",
            {"resource_type": "tag", "resource_id": "../secrets"},
        ),
        (
            "exact UUID",
            "update",
            {
                "resource_type": "tag",
                "resource_id": f"{USER_ID}%2F..",
                "payload": {"name": "t"},
            },
        ),
        (
            "exact UUID",
            "delete",
            {
                "resource_type": "pipeline",
                "resource_id": USER_ID,
                "project_id": "../p",
            },
        ),
        (
            "exact UUID",
            "create",
            {"resource_type": "model_version", "model_id": "a/b", **project},
        ),
        (
            "exact UUID",
            "delete",
            {
                "resource_type": "artifact_version",
                "resource_id": USER_ID,
                "artifact_id": f"{USER_ID}/..",
                **project,
            },
        ),
    ]
    zenml = _ZenML()

    async def run() -> None:
        async with connected(zenml) as mcp:
            for reason, operation, arguments in refusals:
                refused = await mcp.call_tool(
                    f"zenml_{operation}_resource", arguments
                )
                error = _error(refused)
                assert error["kind"] == "invalid_request", (arguments, error)
                assert reason in error["message"], error
                assert value not in error["message"]

    asyncio.run(run())
    assert not zenml.seen, "a refused write still contacted ZenML"


def test_a_generic_write_refuses_the_secret_fields_of_a_flavor() -> None:
    """A field the flavor marks sensitive is refused, whatever its name."""
    value = _never_echoed()
    component = WRITE_GOLDEN["entities"]["stack_component"]
    properties = {"key": {"type": "string", "sensitive": True}, "path": {}}
    flavor = WRITE_GOLDEN["entities"]["flavor"] | {
        "metadata": {"config_schema": {"properties": properties}}
    }
    page = {
        "index": 1,
        "max_size": 20,
        "total_pages": 1,
        "total": 1,
        "items": [flavor],
    }
    zenml = _ZenML(
        {
            "/api/v1/flavors": lambda _: _json(page),
            "/api/v1/components": lambda _: _json(component),
            f"/api/v1/components/{component['id']}": lambda _: _json(
                component
            ),
        }
    )
    configuration = {"path": "s3://bucket", "key": value}
    kind = "orchestrator"
    new = {"name": "c", "flavor": "s3", "component_type": kind}
    writes: list[tuple[str, dict[str, Any]]] = [
        ("create", {"payload": {**new, "configuration": configuration}}),
        (
            "update",
            {
                "resource_id": component["id"],
                "component_type": kind,
                "payload": {"configuration": configuration},
            },
        ),
    ]

    async def run() -> None:
        async with connected(zenml) as mcp:
            for operation, arguments in writes:
                refused = await mcp.call_tool(
                    f"zenml_{operation}_resource",
                    {"resource_type": "stack_component", **arguments},
                )
                error = _error(refused)
                assert error["kind"] == "invalid_request", (operation, error)
                assert "'configuration.key'" in error["message"], error
                assert value not in error["message"]

    asyncio.run(run())
    written = [r for r in zenml.seen if r["method"] in ("POST", "PUT")]
    assert not written, f"a flavor's secret field reached ZenML: {written}"


def test_an_action_is_refused_before_anything_reaches_zenml() -> None:
    """Actions not offered, credential-like keys and ids off their route.

    A webhook's `rotate_secret` is not refused here: without a secret page
    its secret is sent.
    """
    value = _never_echoed()
    project = {"project_id": GOLDEN["project"]}
    deployment = {
        "resource_type": "deployment",
        "resource_id": USER_ID,
        **project,
    }
    run_ = {
        "resource_type": "pipeline_run",
        "action": "replay",
        "resource_id": USER_ID,
    }
    trigger = {
        "resource_type": "schedule_trigger",
        "resource_id": USER_ID,
        **project,
    }
    overrides = {"step_input_overrides": {"train": {"api_token": value}}}
    refusals: list[tuple[str, dict[str, Any]]] = [
        ("does not offer", {**deployment, "action": "provision"}),
        ("does not offer", {**deployment, "action": "deprovision"}),
        ("does not offer", {**deployment, "action": "refresh"}),
        (
            "api_token",
            {**run_, "payload": {"run_configuration": overrides}, **project},
        ),
        (
            "password",
            {
                "resource_type": "run_wait_condition",
                "action": "resolve",
                "resource_id": USER_ID,
                "payload": {
                    "resolution": "CONTINUE",
                    "result": {"password": value},
                },
                **project,
            },
        ),
        ("exact UUID", {**run_, "resource_id": "../runs", **project}),
        ("exact UUID", {**run_, "project_id": f"{USER_ID}%2F.."}),
        (
            "snapshot_id",
            {
                **trigger,
                "action": "detach",
                "payload": {"snapshot_id": "../x"},
            },
        ),
        (
            "target_id",
            {
                "resource_type": "tag",
                "action": "attach",
                "resource_id": USER_ID,
                "payload": {"target_type": "pipeline", "target_id": "a/b"},
                **project,
            },
        ),
    ]
    zenml = _ZenML()

    async def run() -> None:
        async with connected(zenml) as mcp:
            for reason, arguments in refusals:
                refused = await mcp.call_tool(
                    "zenml_action_resource", arguments
                )
                error = _error(refused)
                assert error["kind"] == "invalid_request", (arguments, error)
                assert reason in error["message"], error
                assert value not in error["message"]

    asyncio.run(run())
    assert not zenml.seen, "a refused action still contacted ZenML"


def test_an_artifact_version_that_runs_use_keeps_its_metadata() -> None:
    """The SDK checks this before it sends the delete, so the tool does too."""
    version = WRITE_GOLDEN["entities"]["artifact_version"]
    zenml = _ZenML(
        {
            f"/api/v1/artifact_versions/{version['id']}": lambda _: _json(
                version
            ),
            "/api/v1/artifact_versions": lambda _: _json({"items": []}),
        }
    )

    async def run() -> Any:
        async with connected(zenml) as mcp:
            return await mcp.call_tool(
                "zenml_delete_resource",
                {
                    "resource_type": "artifact_version",
                    "resource_id": version["id"],
                    "artifact_id": version["body"]["artifact"]["id"],
                    "project_id": WRITE_GOLDEN["project"],
                },
            )

    refused = asyncio.run(run())
    assert _error(refused)["kind"] == "invalid_request"
    assert "DELETE" not in {r["method"] for r in zenml.seen}


def test_a_platform_event_trigger_is_switched_off_with_its_stored_source() -> (
    None
):
    """An update that names no source keeps the one ZenML holds."""
    trigger = WRITE_GOLDEN["entities"]["platform_event_trigger"]
    pipeline = WRITE_GOLDEN["entities"]["pipeline"]
    source = trigger["body"]["source_entity"]
    assert (source["type"], source["id"]) == ("pipeline", pipeline["id"])
    zenml = _ZenML(
        {
            f"/api/v1/triggers/{trigger['id']}": lambda _: _json(trigger),
            f"/api/v1/pipelines/{pipeline['id']}": lambda _: _json(pipeline),
        }
    )

    async def run() -> Any:
        async with connected(zenml) as mcp:
            return await mcp.call_tool(
                "zenml_update_resource",
                {
                    "resource_type": "platform_event_trigger",
                    "resource_id": trigger["id"],
                    "project_id": WRITE_GOLDEN["project"],
                    "payload": {"active": False},
                },
            )

    result = asyncio.run(run())
    assert not result.is_error, result.structured_content
    (put,) = [r for r in zenml.seen if r["method"] == "PUT"]
    assert put["body"]["source_entity"] == source
    assert put["body"]["active"] is False


@pytest.mark.parametrize(
    "info",
    [
        lambda: _json({"detail": "down"}, 503),
        lambda: httpx.Response(200, text="<html>proxy sign-in</html>"),
    ],
    ids=["unavailable", "not_json"],
)
@pytest.mark.parametrize(
    "tool", ["zenml_run_snapshot", "zenml_replay_pipeline_run"]
)
def test_a_started_run_is_returned_when_its_link_cannot_be_read(
    tool: str, info: Callable[[], httpx.Response]
) -> None:
    """The run exists once ZenML started it; only its link is left out.

    An error here would invite a retry, which starts a second run.

    Args:
        tool: A tool that starts a run.
        info: Builds ZenML's answer to the server info read for the link.
    """
    run = WRITE_GOLDEN["entities"]["pipeline_run"]
    snapshot = str(uuid.uuid4())
    zenml = _ZenML(
        {
            f"/api/v1/pipeline_snapshots/{snapshot}/runs": lambda _: _json(
                run
            ),
            f"/api/v1/runs/{run['id']}": lambda _: _json(run),
            f"/api/v1/runs/{run['id']}/replay": lambda _: _json(run),
            "/api/v1/info": lambda _: info(),
        }
    )
    arguments = (
        {"snapshot_id": snapshot}
        if tool == "zenml_run_snapshot"
        else {"run": run["id"]}
    )

    async def start() -> Any:
        # A server of its own: no other test's server info is cached for it.
        cold = f"https://{uuid.uuid4().hex}.example"
        async with connected(zenml, server_url=cold) as mcp:
            return await mcp.call_tool(tool, arguments)

    result = asyncio.run(start())
    assert not result.is_error, result.structured_content
    assert result.structured_content["outcome"] == "started"
    assert result.structured_content["run"]["id"] == run["id"]
    assert "dashboard_url" not in result.structured_content["run"]


def test_starting_a_run_refuses_credentials_and_a_missing_target() -> None:
    """Credentials, no target, internal fields and two targets at once."""
    value = _never_echoed()
    in_a_step = {"steps": {"train": {"parameters": {"api_token": value}}}}
    in_the_environment = {"environment": {"DB_PASSWORD": value}}
    model = {"model": {"name": "m", "model_version_id": "v"}}
    refusals: dict[str, dict[str, Any]] = {
        "api_token": {
            "snapshot_name_or_id": "s",
            "run_configuration": in_a_step,
        },
        "DB_PASSWORD": {
            "template_id": "t",
            "run_configuration": in_the_environment,
        },
        "at least one of": {
            "pipeline_name_or_id": "",
            "stack_name_or_id": "p",
        },
        "internal use only": {
            "snapshot_name_or_id": "s",
            "run_configuration": model,
        },
        "mutually exclusive": {
            "snapshot_name_or_id": "s",
            "template_id": "t",
        },
    }
    zenml = _ZenML()

    async def run() -> None:
        async with connected(zenml) as mcp:
            for reason, arguments in refusals.items():
                refused = await mcp.call_tool(
                    "zenml_trigger_pipeline", arguments
                )
                error = _error(refused)
                assert error["kind"] == "invalid_request", error
                assert reason in error["message"], error
                assert value not in error["message"]

    asyncio.run(run())
    assert not zenml.seen, "a refused start still contacted ZenML"


def test_a_snapshot_run_refuses_credentials_before_anything_is_sent() -> None:
    """A credential-like step parameter is refused by name, not by value."""
    value = _never_echoed()
    step_parameters = {"train": {"api_" + "token": value}}
    zenml = _ZenML()

    async def run() -> Any:
        async with connected(zenml) as mcp:
            return await mcp.call_tool(
                "zenml_run_snapshot",
                {"snapshot_id": "s", "step_parameters": step_parameters},
            )

    error = _error(asyncio.run(run()))
    assert error["kind"] == "invalid_request", error
    assert "api_token" in error["message"]
    assert value not in error["message"]
    assert not zenml.seen, "a refused run still contacted ZenML"


def test_a_list_page_outside_the_limits_is_refused_before_any_request() -> (
    None
):
    """A page below 1 or a size outside 1 to 200 is refused as such."""
    page = "page must be an integer greater than or equal to 1"
    size = "size must be between 1 and 200"
    zenml = _ZenML()

    async def run() -> None:
        async with connected(zenml) as mcp:
            for arguments, message in (
                ({"size": 0}, size),
                ({"size": 201}, size),
                ({"page": 0}, page),
            ):
                refused = await mcp.call_tool(
                    "zenml_list_pipeline_runs", arguments
                )
                error = _error(refused)
                assert (error["kind"], error["message"]) == (
                    "invalid_request",
                    message,
                )

    asyncio.run(run())
    assert not zenml.seen, "a refused list still contacted ZenML"


def test_a_generic_list_resolves_the_project_before_its_filters() -> None:
    """mcp-zenml resolves the project first: a bad one wins over a bad filter."""
    zenml = _ZenML()

    async def run() -> None:
        async with connected(zenml) as mcp:
            for arguments, message in (
                (
                    {"resource_type": "user", "project_id": USER_ID},
                    "'user' is global and does not accept project_id",
                ),
                (
                    {"resource_type": "pipeline", "project_id": "p"},
                    "project_id must be a non-empty UUID",
                ),
            ):
                refused = await mcp.call_tool(
                    "zenml_list_resources",
                    {**arguments, "filters": {"bogus": "x"}},
                )
                error = _error(refused)
                assert (error["kind"], error["message"]) == (
                    "invalid_request",
                    message,
                )

    asyncio.run(run())


def test_a_create_outside_the_default_project_is_refused_as_upstream_words_it() -> (  # noqa: E501
    None
):
    """The project is checked first, so it wins over an id a create ignores."""
    zenml = _ZenML(
        {"/api/v1/projects/p1": lambda _: _json({"id": GOLDEN["project"]})}
    )
    create = {
        "resource_type": "model",
        "payload": {"name": "m"},
        "project_id": USER_ID,
    }

    async def run() -> None:
        async with connected(zenml) as mcp:
            for arguments in (create, {**create, "model_id": USER_ID}):
                refused = await mcp.call_tool(
                    "zenml_create_resource", arguments
                )
                error = _error(refused)
                assert (error["kind"], error["message"]) == (
                    "invalid_request",
                    "The requested project is not the client's active project",
                )

    asyncio.run(run())
    assert "/api/v1/models" not in {r["path"] for r in zenml.seen}


def _page(*items: dict[str, Any]) -> httpx.Response:
    shape = {"index": 1, "total_pages": 1, "total": len(items)}
    return _json({**shape, "items": list(items)})


def test_a_pipeline_without_a_runnable_snapshot_starts_nothing() -> None:
    """No snapshot to run is not found, and no run is started."""
    training = {"id": "pipeline-1", "body": {"project_id": PROJECT_IDS[0]}}
    zenml = _ZenML(
        {
            "/api/v1/projects/p1": lambda _: _json({"id": PROJECT_IDS[0]}),
            "/api/v1/pipelines": lambda _: _page(training),
            "/api/v1/pipeline_snapshots": lambda _: _page(),
        }
    )

    async def run() -> Any:
        async with connected(zenml) as mcp:
            return await mcp.call_tool(
                "zenml_trigger_pipeline", {"pipeline_name_or_id": "t"}
            )

    assert _error(asyncio.run(run()))["kind"] == "not_found"
    assert not [r for r in zenml.seen if r["path"].endswith("/runs")]


def test_a_generic_get_cannot_leave_its_route_and_masks_credentials() -> None:
    """An id with a path in it is refused, and credential metadata is masked."""
    step = {
        "id": USER_ID,
        "body": {"project_id": GOLDEN["project"]},
        "metadata": {
            "pipeline_run_id": USER_ID,
            "run_metadata": {
                "pwd": "hunter2",
                "db_password": "x",
                "epochs": 3,
            },
        },
    }
    zenml = _ZenML(
        {
            f"/api/v1/steps/{USER_ID}": lambda _: _json(step),
            "/api/v1/projects/p1": lambda _: _json({"id": GOLDEN["project"]}),
        }
    )
    run_ = {"pipeline_run_id": USER_ID}

    async def run() -> Any:
        async with connected(zenml) as mcp:
            for resource_id in ("../secrets", "..", "a/b", "a\\b"):
                refused = await mcp.call_tool(
                    "zenml_get_resource",
                    {
                        "resource_type": "run_step",
                        "resource_id": resource_id,
                        **run_,
                    },
                )
                assert _error(refused)["kind"] == "invalid_request"
            await mcp.call_tool(
                "zenml_get_resource",
                {
                    "resource_type": "service_connector_type",
                    "resource_id": "aws%2F..",
                },
            )
            return await mcp.call_tool(
                "zenml_get_resource",
                {"resource_type": "run_step", "resource_id": USER_ID, **run_},
            )

    read = asyncio.run(run())
    assert {r["path"] for r in zenml.seen} == {
        "/api/v1/service_connector_types/aws%2F..",
        f"/api/v1/steps/{USER_ID}",
        "/api/v1/current-user",
        "/api/v1/projects/p1",
    }
    item = read.structured_content["item"]
    assert item["metadata"]["run_metadata"] == {"pwd": "***", "epochs": 3}


LogPage = Union[int, dict[str, Any], tuple[list[str], Optional[str], Any]]


def _log_pages(pages: dict[Optional[str], LogPage]) -> dict[str, Route]:
    """A step whose log store serves `pages`, keyed by the cursor requested.

    A page is a status to fail with, a body to send as is, or the lines with
    the `before` and `after` cursors.

    Args:
        pages: The pages.

    Returns:
        The fake ZenML's routes.
    """

    def entries(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        page = pages[params.get("before") or params.get("after")]
        if isinstance(page, int):
            return _json({"detail": "down"}, page)
        if not isinstance(page, tuple):
            return _json(page)
        lines, before, after = page
        items = [{"message": line} for line in lines]
        return _json({"items": items, "before": before, "after": after})

    step = {
        "id": "s1",
        "name": "train",
        "body": {"status": "failed"},
        "resources": {
            "log_collection": [{"id": "l1", "body": {"source": "step"}}]
        },
    }
    return {
        "/api/v1/steps/s1": lambda _: _json(step),
        "/api/v1/logs/l1/entries": entries,
    }


@pytest.mark.parametrize(
    ("pages", "arguments", "logs", "truncated", "note"),
    [
        pytest.param(
            {None: (["a"], None, "p2"), "p2": (["b"], None, None)},
            {},
            "a\nb",
            False,
            None,
            id="forward-to-the-end",
        ),
        pytest.param(
            {None: (["x" * 60_000, "newest"], None, None)},
            {},
            "x" * 9_991 + " …[cut]\nnewest",
            True,
            "1 of these lines was cut at 10,000 characters, and the rest of "
            "it can't be read through this tool.",
            id="a-long-line-is-cut-and-does-not-push-out-the-newest",
        ),
        pytest.param(
            {None: (["c"], "p1", None), "p1": (["a", "b"], "p0", None)},
            {"tail": 3},
            "a\nb\nc",
            True,
            "older",
            id="back-until-tail-is-met",
        ),
        pytest.param(
            {None: (["ok"], "p1", None), "p1": (["boom"], None, None)},
            {"tail": 1, "contains": "BOOM"},
            "boom",
            False,
            None,
            id="contains-looks-past-pages-without-a-match",
        ),
        pytest.param(
            {None: (["a"], None, "p2"), "p2": 503},
            {},
            "a",
            True,
            "newer",
            id="failed-page-keeps-what-was-read",
        ),
        pytest.param(
            {None: (["a"], None, "p2"), "p2": {"items": [{"timestamp": 42}]}},
            {},
            "a",
            True,
            "newer",
            id="malformed-page-keeps-what-was-read",
        ),
        pytest.param(
            {
                None: (["a"], None, "p2"),
                "p2": ([], None, "p3"),
                "p3": (["b"], None, None),
            },
            {},
            "a\nb",
            False,
            None,
            id="empty-page-with-a-cursor-is-not-the-end",
        ),
        pytest.param(
            {None: (["a"], None, "same"), "same": (["b"], None, "same")},
            {},
            "a\nb",
            True,
            "repeated",
            id="repeating-cursor-does-not-invent-lines",
        ),
        pytest.param(
            {
                None: (["a"], None, "1"),
                **{str(n): (["a"], None, str(n + 1)) for n in range(1, 150)},
            },
            {"tail": 1},
            "a",
            True,
            "newer",
            id="fresh-cursors-stop-at-the-page-budget",
        ),
    ],
)
def test_step_logs_follow_cursors_and_report_gaps(
    pages: dict[Optional[str], LogPage],
    arguments: dict[str, Any],
    logs: str,
    truncated: bool,
    note: Optional[str],
) -> None:
    """Step logs follow the log store's cursors and say what they missed.

    Args:
        pages: The log store's pages, by cursor.
        arguments: The call's arguments besides the step.
        logs: The logs the call returns.
        truncated: Whether it says some were left out.
        note: Text its note holds, or None for no note.
    """
    zenml = _ZenML(_log_pages(pages))

    async def run() -> Any:
        async with connected(zenml) as mcp:
            return await mcp.call_tool(
                "zenml_get_step_logs", {"step_run_id": "s1", **arguments}
            )

    content = asyncio.run(run()).structured_content
    assert content["logs"] == logs, content
    assert content["truncated"] is truncated, content
    if note:
        assert note in content["note"], content
    else:
        assert content["note"] is None, content


def test_step_logs_do_not_hide_a_rejected_session_on_a_later_page() -> None:
    """A 401 the client can't renew on a later page fails the whole read."""
    zenml = _ZenML(_log_pages({None: (["a"], None, "p2"), "p2": 401}))

    async def run() -> Any:
        async with connected(zenml) as mcp:
            return await mcp.call_tool(
                "zenml_get_step_logs", {"step_run_id": "s1"}
            )

    result = asyncio.run(run())
    assert _error(result)["kind"] == "unauthenticated", result


NEXT_STEPS = {
    403: (
        "permission_denied",
        "If this is about access, ask a workspace admin for it; "
        "signing in again won't help.",
    ),
    404: ("not_found", "Check the name or id, for example with a list tool."),
    409: (
        "already_exists",
        "Choose another name, or update the existing one.",
    ),
    429: ("rate_limited", "Wait a minute and try again."),
    500: (
        "unavailable",
        "If ZenML's reason doesn't say what to change, try again shortly.",
    ),
}
_ID = "11111111-2222-4333-8444-555555555555"
_EMPTY_PAGE = {"items": [], "total": 0, "index": 1, "total_pages": 1}


@pytest.mark.parametrize(
    ("name", "arguments", "answers", "kind", "next_step"),
    [
        pytest.param(
            "zenml_list_stacks",
            {},
            {"/api/v1/stacks": ({"detail": "Request Timeout"}, 408)},
            "unavailable",
            "Try again shortly.",
            id="408",
        ),
        pytest.param(
            "zenml_list_stacks",
            {},
            {"/api/v1/stacks": (None, 503)},
            "unavailable",
            "Try again shortly.",
            id="5xx-without-a-reason",
        ),
        pytest.param(
            "zenml_list_stacks",
            {},
            {"/api/v1/stacks": ({"detail": "Not Found"}, 404)},
            "not_found",
            "This workspace's ZenML version doesn't support it.",
            id="route-missing",
        ),
        pytest.param(
            "zenml_get_step_source_code",
            {"step_run_id": _ID},
            {
                f"/api/v1/steps/{_ID}": (
                    {"detail": ["KeyError", "No step"]},
                    404,
                )
            },
            "not_found",
            NEXT_STEPS[404][1],
            id="step-source-404",
        ),
        pytest.param(
            "zenml_get_model_version",
            {"model": _ID},
            {
                "/api/v1/model_versions": (_EMPTY_PAGE, 200),
                f"/api/v1/models/{_ID}": (
                    {"detail": ["KeyError", "No model"]},
                    404,
                ),
            },
            "not_found",
            NEXT_STEPS[404][1],
            id="model-version-404",
        ),
    ],
)
def test_a_refused_read_ends_with_the_next_step_that_fits(
    name: str,
    arguments: dict[str, Any],
    answers: dict[str, tuple[Any, int]],
    kind: str,
    next_step: str,
) -> None:
    """A refused read is labeled by its status and ends with what to do.

    Args:
        name: The tool.
        arguments: Its arguments.
        answers: ZenML's body and status, by path; a None body is empty.
        kind: The error's kind.
        next_step: The message's last sentence.
    """

    def answer(body: Any, status: int) -> Route:
        if body is None:
            return lambda _: httpx.Response(status, text="")
        return lambda _: _json(body, status)

    zenml = _ZenML({route: answer(*reply) for route, reply in answers.items()})

    async def run() -> Any:
        async with connected(zenml) as mcp:
            return await mcp.call_tool(name, arguments)

    result = asyncio.run(run())
    error = _error(result)
    assert error["kind"] == kind, result
    assert error["message"].endswith(next_step), result
    assert not zenml.unscripted, zenml.unscripted


@pytest.mark.parametrize("status", sorted(NEXT_STEPS))
def test_a_refused_create_says_what_happened_and_what_to_do_next(
    status: int,
) -> None:
    """A named and a generic create that ZenML refuses.

    The kind follows the status, and the message keeps ZenML's reason and
    ends with the next step. A refused create is not sent again.

    Args:
        status: ZenML's status.
    """
    kind, next_step = NEXT_STEPS[status]
    reason = "Entity with name 'taken' already exists"

    def refused(_: httpx.Request) -> httpx.Response:
        return _json({"detail": ["SomeError", reason]}, status)

    zenml = _ZenML({"/api/v1/stacks": refused, "/api/v1/tags": refused})
    components = {
        "orchestrator": "11111111-2222-4333-8444-555555555555",
        "artifact_store": "66666666-7777-4888-8999-aaaaaaaaaaaa",
    }
    calls = {
        "zenml_create_stack": {"name": "taken", "components": components},
        "zenml_create_resource": {
            "resource_type": "tag",
            "payload": {"name": "taken", "exclusive": False},
        },
    }

    async def run() -> None:
        async with connected(zenml) as mcp:
            for name, arguments in calls.items():
                result = await mcp.call_tool(name, arguments)
                error = _error(result)
                assert result.is_error, (name, result)
                assert error["kind"] == kind, (name, error)
                assert reason in error["message"], (name, error)
                assert error["message"].endswith(next_step), (name, error)

    asyncio.run(run())
    creates = [
        r
        for r in zenml.seen
        if r["path"] in {"/api/v1/stacks", "/api/v1/tags"}
    ]
    assert len(creates) == len(calls), "a refused create was sent again"


class _CountedToken(ZenMLAuth):
    """A token that counts how often it is asked for or renewed."""

    def __init__(self) -> None:
        super().__init__()
        self.asked = 0
        self.renewed = 0

    async def token(self) -> str:
        self.asked += 1
        return "token-sample"

    async def renew(self, rejected: str) -> str:
        self.renewed += 1
        raise ZenMLAuthError("the session was refused")


@pytest.mark.parametrize("status", [403, 429])
def test_a_refused_step_log_read_says_why_without_signing_in_again(
    status: int,
) -> None:
    """A step-log read refused for permission or rate is labeled by status.

    The session is neither renewed nor asked for again.

    Args:
        status: ZenML's status.
    """
    kind, next_step = NEXT_STEPS[status]
    denied = {"detail": ["IllegalOperationError", "not allowed"]}
    # The read starts at either route: a server once seen without the
    # entries route goes straight to the older one.
    routes = ("/api/v1/steps/s1", "/api/v1/steps/s1/logs")
    zenml = _ZenML(
        {route: lambda _: _json(denied, status) for route in routes}
    )
    auth = _CountedToken()

    def counted(client: ZenMLRestClient) -> ZenMLCall:
        client.auth = auth
        return ZenMLCall(client)

    async def run() -> Any:
        async with connected(zenml, call=counted) as mcp:
            arguments = {"step_run_id": "s1"}
            result = await mcp.call_tool(
                "zenml_get_step_log_entries", arguments
            )
            await mcp.call_tool("zenml_get_step_log_entries", arguments)
            return result

    result = asyncio.run(run())
    error = _error(result)
    assert error["kind"] == kind, result
    assert error["message"].endswith(next_step), result
    reads = [r for r in zenml.seen if r["path"] in routes]
    assert len(reads) == 2, "a refused read was sent again"
    assert (auth.asked, auth.renewed) == (1, 0), (
        f"a {status} led to another sign-in"
    )


def _step_error(detail: str) -> str:
    """The message of a step-log read that ZenML refuses with `detail`.

    Args:
        detail: ZenML's reason.

    Returns:
        The tool's error message.
    """
    error = ["E", detail]
    zenml = _ZenML(
        {"/api/v1/steps/s1": lambda _: _json({"detail": error}, 400)}
    )

    async def run() -> Any:
        async with connected(zenml) as mcp:
            return await mcp.call_tool(
                "zenml_get_step_logs", {"step_run_id": "s1"}
            )

    message: str = _error(asyncio.run(run()))["message"]
    return message


def test_a_zenml_error_keeps_its_reason_and_masks_credentials() -> None:
    """URL logins, password fields, API keys and bearer tokens are masked."""
    message = _step_error(
        "Stack check failed: postgres://bob:hunter2@db/x, password=hunter3, "
        'ZENKEY_hunter4, {"api_key": "hunter5 hunter7"}, '
        "Authorization: Bearer hunter6"
    )
    assert "Stack check failed" in message, message
    assert "hunter" not in message, message


def test_a_zenml_error_masks_a_sign_in_code_and_keeps_the_rest() -> None:
    """A URL's `code` is masked wherever it is; the rest of the URL is kept."""
    code = "-".join(("Ab", "1_x.y~z/+=%2F"))
    message = _step_error(
        f"Callback failed: https://mcp.example/cb?code={code}&state=s1 "
        "(error_code=E42, status_code=400) or "
        f"https://mcp.example/cb?state=s2&CODE={code} instead. "
        f"Also https://mcp.example/cb#code={code}&state=s3 and "
        f"https://mcp.example/cb?state=s4&amp;code={code} "
        f'with password="https://mcp.example/cb?code={code}\\" hidden-tail" '
        "kept."
    )
    assert (
        "Callback failed: https://mcp.example/cb?code=***&state=s1 "
        "(error_code=E42, status_code=400) or "
        "https://mcp.example/cb?state=s2&CODE=*** instead."
    ) in message, message
    assert "with password=*** kept." in message, message
    assert "hidden-tail" not in message, message
    assert "https://mcp.example/cb#code=***&state=s3" in message, message
    assert "https://mcp.example/cb?state=s4&amp;code=***" in message, message
    assert code not in message, message


def test_a_list_answer_from_a_newer_or_older_server_still_reads() -> None:
    """Unknown fields are ignored and a missing count comes from the items.

    A page with no items is an answer the tool can't read, not a crash.
    """
    training = {
        "id": PROJECT_IDS[1],
        "name": "training",
        "body": {"project_id": PROJECT_IDS[0]},
        "added": 1,
    }
    answers: list[dict[str, Any]] = [
        {"items": [training], "cursor": "new-field"},
        {"total": 1},
    ]
    zenml = _ZenML(
        {
            "/api/v1/projects/p1": lambda _: _json({"id": PROJECT_IDS[0]}),
            "/api/v1/pipelines": lambda _: _json(answers.pop(0)),
        }
    )
    lookup = {"resource_type": "pipeline", "resource_id": "training"}

    async def run() -> tuple[Any, Any]:
        async with connected(zenml) as mcp:
            found = await mcp.call_tool("zenml_get_resource", lookup)
            unreadable = await mcp.call_tool("zenml_get_resource", lookup)
            return found, unreadable

    found, unreadable = asyncio.run(run())
    assert found.structured_content["item"]["name"] == "training", found
    assert _error(unreadable)["kind"] == "unavailable"
    assert not zenml.unscripted, zenml.unscripted


def _long_log(lines: list[str]) -> dict[str, Route]:
    """A step whose log store pages back from the newest entry, 1,000 a page.

    The step's older logs route, which the tools may prefer for a server
    seen without the entries route, answers the whole log.

    Args:
        lines: The log, oldest first.

    Returns:
        The fake ZenML's routes.
    """

    def entries(request: httpx.Request) -> httpx.Response:
        before = request.url.params.get("before")
        end = int(before) if before else len(lines)
        start = max(0, end - 1000)
        items = [{"message": line} for line in lines[start:end]]
        older = str(start) if start else None
        return _json({"items": items, "before": older})

    step = {
        "id": "s1",
        "name": "train",
        "body": {"status": "failed"},
        "resources": {
            "log_collection": [{"id": "l1", "body": {"source": "step"}}]
        },
    }
    return {
        "/api/v1/steps/s1": lambda _: _json(step),
        "/api/v1/logs/l1/entries": entries,
        "/api/v1/steps/s1/logs": lambda _: _json(
            [{"message": line} for line in lines]
        ),
    }


def _cursor_of(value: Any) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(value).encode()).decode()
    return encoded.rstrip("=")


def _text_of(result: Any) -> str:
    text: str = result.content[0].text
    return text


def test_a_long_log_is_read_in_parts_that_fit_without_gap_or_overlap() -> None:
    """Escaped characters count: each answer is measured as clients get it.

    A forged cursor is refused.
    """
    lines = [
        f'{n} "said" \\ path\tcol {"x" * (n % 40)}{n}' for n in range(20_000)
    ]
    zenml = _ZenML(_long_log(lines))
    read: list[str] = []

    async def run() -> None:
        async with connected(zenml) as mcp:
            cursor = None
            while True:
                more = {"cursor": cursor} if cursor else {}
                result = await mcp.call_tool(
                    "zenml_get_step_logs",
                    {"step_run_id": "s1", "tail": 5000, **more},
                )
                assert len(_text_of(result)) <= 40_000, len(read)
                content = result.structured_content
                read[:0] = content["logs"].split("\n")
                cursor = content["cursor"]
                if cursor is None:
                    break
                assert content["shown_lines"] < 5000, "no size limit was hit"
                assert f'cursor="{cursor}"' in content["note"], content
            for forged in (
                "not a cursor!",
                _cursor_of({"skip": True}),
                _cursor_of({"skip": 0}),
                _cursor_of({"skip": 1, "step_run_id": "s2"}),
            ):
                refused = await mcp.call_tool(
                    "zenml_get_step_logs",
                    {"step_run_id": "s1", "cursor": forged},
                )
                assert _error(refused)["kind"] == "invalid_request"

    asyncio.run(run())
    assert read == lines


def test_log_entries_default_to_the_newest_200_and_page_back() -> None:
    """The newest 200 entries, then older ones by cursor, up to a tail of 1000."""
    lines = [f"entry {n} " + "y" * 60 for n in range(3000)]
    zenml = _ZenML(_long_log(lines))

    async def run() -> tuple[Any, Any, Any]:
        async with connected(zenml) as mcp:
            newest = await mcp.call_tool(
                "zenml_get_step_log_entries", {"step_run_id": "s1"}
            )
            cursor = newest.structured_content["cursor"]
            older = await mcp.call_tool(
                "zenml_get_step_log_entries",
                {"step_run_id": "s1", "tail": 1000, "cursor": cursor},
            )
            refused = await mcp.call_tool(
                "zenml_get_step_log_entries",
                {"step_run_id": "s1", "tail": 1001},
            )
            return newest, older, refused

    newest, older, refused = asyncio.run(run())
    first = newest.structured_content
    assert [e["message"] for e in first["logs"]] == lines[-200:]
    assert first["possibly_truncated"] is True
    assert len(_text_of(older)) <= 40_000
    shown = [e["message"] for e in older.structured_content["logs"]]
    assert 0 < len(shown) < 1000, "the size limit was not reached"
    assert shown == lines[-200 - len(shown) : -200]
    assert _error(refused)["kind"] == "invalid_request"


@pytest.mark.parametrize(
    "name", ["zenml_get_step_code", "zenml_get_step_source_code"]
)
def test_step_code_is_read_in_line_ranges(name: str) -> None:
    """Long code comes back in line ranges that fit, and a range on request.

    Args:
        name: The tool.
    """
    code = "\n".join(
        f'    value_{n} = compute({n}, "text")  # line {n}'
        for n in range(1, 3001)
    )
    step = {
        "id": "s1",
        "name": "train",
        "body": {},
        "metadata": {"source_code": code},
    }
    zenml = _ZenML({"/api/v1/steps/s1": lambda _: _json(step)})
    parts: list[str] = []

    async def run() -> Any:
        async with connected(zenml) as mcp:
            start = 1
            while True:
                result = await mcp.call_tool(
                    name, {"step_run_id": "s1", "start_line": start}
                )
                assert len(_text_of(result)) <= 40_000
                content = result.structured_content
                assert (content["first_line"], content["total_lines"]) == (
                    start,
                    3000,
                )
                parts.append(content["source_code"])
                if not content["truncated"]:
                    break
                start = content["last_line"] + 1
                assert f"start_line={start}" in content["note"], content
            return await mcp.call_tool(
                name, {"step_run_id": "s1", "start_line": 10, "end_line": 12}
            )

    middle = asyncio.run(run())
    assert len(parts) > 1
    assert "".join(parts) == code
    assert middle.structured_content["source_code"] == "".join(
        code.splitlines(keepends=True)[9:12]
    )


def test_a_pipeline_reads_at_most_four_run_graphs_at_once() -> None:
    """Ten runs' graphs are read, no more than four at a time."""
    in_flight = most = 0

    async def graph(_: httpx.Request) -> httpx.Response:
        nonlocal in_flight, most
        in_flight += 1
        most = max(most, in_flight)
        # Lets every other graph read that may start do so first.
        for _ in range(50):
            await asyncio.sleep(0)
        in_flight -= 1
        return _json({"nodes": [], "edges": []})

    def page(*items: dict[str, Any]) -> httpx.Response:
        return _json({"index": 1, "total_pages": 1, "items": list(items)})

    pipeline = {
        "id": PROJECT_IDS[1],
        "name": "train",
        "body": {"project_id": "p1"},
    }
    runs = [
        {"id": f"r{n}", "body": {"status": "completed"}} for n in range(10)
    ]
    zenml = _ZenML(
        {
            f"/api/v1/pipelines/{PROJECT_IDS[1]}": lambda _: _json(pipeline),
            "/api/v1/runs": lambda _: page(*runs),
            "/api/v1/pipeline_snapshots": lambda _: page(),
            "/api/v1/projects/p1": lambda _: _json({"id": "p1", "name": "p"}),
            **{f"/api/v1/runs/r{n}/dag": graph for n in range(10)},
        }
    )

    async def run() -> Any:
        async with connected(zenml) as mcp:
            return await mcp.call_tool(
                "zenml_get_pipeline", {"pipeline": PROJECT_IDS[1]}
            )

    result = asyncio.run(run())
    assert "error" not in result.structured_content, result
    assert len([r for r in zenml.seen if r["path"].endswith("/dag")]) == 10
    assert most == 4


@pytest.mark.parametrize(("built", "reads"), [(False, 5), (True, 20)])
def test_the_snapshot_search_stops_at_100_snapshots_or_20_builds(
    built: bool, reads: int
) -> None:
    """The search for a runnable snapshot gives up and says what to pass.

    Args:
        built: Whether each snapshot has a build to read.
        reads: The snapshot pages or builds read before it gives up.
    """

    def snapshots(request: httpx.Request) -> httpx.Response:
        index = int(request.url.params.get("page", "1"))
        items = [
            {
                "id": f"s{index}-{n}",
                "resources": {"build": {"id": f"b{index}-{n}"}}
                if built
                else {},
            }
            for n in range(20)
        ]
        return _json({"index": index, "total_pages": 50, "items": items})

    training = {"id": "pipeline-1", "body": {"project_id": PROJECT_IDS[0]}}
    builds: dict[str, Route] = {
        f"/api/v1/pipeline_builds/b{i}-{n}": lambda _: _json({"metadata": {}})
        for i in range(1, 51)
        for n in range(20)
    }
    zenml = _ZenML(
        {
            "/api/v1/projects/p1": lambda _: _json({"id": PROJECT_IDS[0]}),
            "/api/v1/pipelines": lambda _: _page(training),
            "/api/v1/pipeline_snapshots": snapshots,
            **builds,
        }
    )

    async def run() -> Any:
        async with connected(zenml) as mcp:
            return await mcp.call_tool(
                "zenml_trigger_pipeline", {"pipeline_name_or_id": "t"}
            )

    refused = asyncio.run(run())
    search = "/pipeline_builds/" if built else "/pipeline_snapshots"
    assert len([r for r in zenml.seen if search in r["path"]]) == reads
    message = _error(refused)["message"]
    assert "Pass snapshot_name_or_id or template_id" in message, message
    assert not [r for r in zenml.seen if r["path"].endswith("/runs")]


def test_most_recent_runs_reads_at_most_100_runs() -> None:
    """A larger run count is read as one page of 100."""
    page = {
        "index": 1,
        "max_size": 100,
        "total_pages": 1,
        "total": 0,
        "items": [],
    }
    zenml = _ZenML(
        {
            "/api/v1/projects/p1": lambda _: _json({"id": PROJECT_IDS[0]}),
            "/api/v1/runs": lambda _: _json(page),
        }
    )

    async def run() -> None:
        async with connected(zenml) as mcp:
            await result_of(
                mcp,
                "resource://zenml_server/most_recent_runs?run_count={run_count}",
                {"run_count": 10_000},
                resource=True,
            )

    asyncio.run(run())
    sizes = [
        r["params"]["size"] for r in zenml.seen if r["path"].endswith("/runs")
    ]
    assert sizes == [["100"]]


@pytest.mark.parametrize(
    ("name", "arguments", "tagged"),
    [
        ("zenml_list_resources", {"resource_type": "pipeline"}, 1),
        ("zenml_list_pipelines", {}, 11),
    ],
)
@pytest.mark.parametrize(
    ("page", "size", "kept"), [(1, 199, range(40, 50)), (3, 100, [40])]
)
def test_a_large_list_page_is_cut_where_the_next_call_starts(
    name: str,
    arguments: dict[str, Any],
    tagged: int,
    page: int,
    size: int,
    kept: Sequence[int],
) -> None:
    """Between 40 and 49 pipelines fit in an answer.

    Following each answer's `next`, then the next page, reads every pipeline
    from where the first call starts, once.

    Args:
        name: The list tool.
        arguments: Its arguments besides the page.
        tagged: The tags each pipeline has.
        page: The first page asked for.
        size: Its size.
        kept: The number of pipelines the first answer may hold.
    """
    recorded = GOLDEN["entities"]["pipeline"]
    tags = [{"name": f"tag-{n}-" + "t" * 40} for n in range(tagged)]
    pipelines = [
        {
            **recorded,
            "id": str(uuid.UUID(int=n + 1)),
            "name": f"pipeline-{n}",
            "resources": {**recorded.get("resources", {}), "tags": tags},
        }
        for n in range(400)
    ]

    def listing(request: httpx.Request) -> httpx.Response:
        index = int(request.url.params["page"])
        max_size = int(request.url.params["size"])
        items = pipelines[(index - 1) * max_size : index * max_size]
        shape = {
            "index": index,
            "max_size": max_size,
            "total_pages": -(-400 // max_size),
        }
        return _json({**shape, "total": 400, "items": items})

    zenml = _ZenML(
        {
            "/api/v1/projects/p1": lambda _: _json({"id": PROJECT_IDS[0]}),
            "/api/v1/pipelines": listing,
        }
    )
    start = (page - 1) * size
    read: list[str] = []
    answers: list[int] = []

    async def run() -> None:
        nonlocal page, size
        async with connected(zenml) as mcp:
            while True:
                result = await mcp.call_tool(
                    name, {**arguments, "page": page, "size": size}
                )
                assert len(_text_of(result)) <= 40_000
                content = result.structured_content
                read.extend(item["name"] for item in content["items"])
                answers.append(len(content["items"]))
                if "next" in content:
                    assert content["truncated"] is True
                    size = content["next"]["size"]
                    page = content["next"]["page"]
                    assert f"size={size} and page={page}." in content["note"]
                elif len(content["items"]) == size:
                    page += 1
                else:
                    break

    asyncio.run(run())
    assert answers[0] in kept, answers
    assert read == [f"pipeline-{n}" for n in range(start, 400)]


@pytest.mark.parametrize(
    "line",
    [
        '"' * 6000 + "a" * 6000,
        "\\" * 6000 + "a" * 6000,
        "x" + "\n" * 6000 + "a" * 6000,
        "x" + "\t" * 6000 + "a" * 6000,
        "\x00" * 5000 + "a" * 5000,
        "\x00" * 2000 + "a" * 5000,
    ],
    ids=["quote", "backslash", "newline", "tab", "nul", "nul-grows"],
)
def test_a_line_whose_characters_escape_unevenly_is_cut_and_the_call_returns(
    line: str,
) -> None:
    """A line whose characters grow when escaped is cut to fit, as escaped.

    Args:
        line: The line, in the logs and the code.
    """
    step = {
        "id": "s1",
        "name": "train",
        "body": {"status": "failed"},
        "metadata": {"source_code": f"ok\n{line}\nend"},
        "resources": {
            "log_collection": [{"id": "l1", "body": {"source": "step"}}]
        },
    }
    entries = {"items": [{"message": "ok"}, {"message": line}], "before": None}
    zenml = _ZenML(
        {
            "/api/v1/steps/s1": lambda _: _json(step),
            "/api/v1/logs/l1/entries": lambda _: _json(entries),
            "/api/v1/steps/s1/logs": lambda _: _json(entries["items"]),
        }
    )

    async def run() -> list[Any]:
        async with connected(zenml) as mcp:
            return [
                await mcp.call_tool(name, {"step_run_id": "s1"})
                for name in (
                    "zenml_get_step_logs",
                    "zenml_get_step_log_entries",
                    "zenml_get_step_code",
                    "zenml_get_step_source_code",
                )
            ]

    for result in asyncio.run(run()):
        assert len(_text_of(result)) <= 40_000
        content = result.structured_content
        assert "error" not in content, content
        text = content["logs"] if "logs" in content else content["source_code"]
        if isinstance(text, list):
            assert max(encoded_size(entry) for entry in text) <= 10_000
        else:
            assert max(encoded_size(part) for part in text.split("\n")) <= (
                10_000
            )


def _forward_log(
    lines: list[str], fails: Callable[[Optional[str]], bool]
) -> dict[str, Route]:
    """A step whose log store pages forward from the oldest entry.

    It answers 1,000 entries a page, and a 500 when `fails` says so.

    Args:
        lines: The log, oldest first.
        fails: Whether the page after a cursor fails.

    Returns:
        The fake ZenML's routes.
    """

    def entries(request: httpx.Request) -> httpx.Response:
        after = request.url.params.get("after")
        if fails(after):
            return _json({"detail": "boom"}, 500)
        start = int(after) if after else 0
        end = min(len(lines), start + 1000)
        items = [{"message": line} for line in lines[start:end]]
        newer = str(end) if end < len(lines) else None
        return _json({"items": items, "after": newer})

    return {**_long_log(lines), "/api/v1/logs/l1/entries": entries}


def _messages(logs: Any) -> list[str]:
    if isinstance(logs, list):
        return [entry["message"] for entry in logs]
    return logs.split("\n") if logs else []


@pytest.mark.parametrize(
    ("name", "tail"),
    [("zenml_get_step_logs", 5000), ("zenml_get_step_log_entries", 1000)],
)
@pytest.mark.parametrize("failing", [1, 2], ids=["first-call", "later-call"])
def test_a_forward_log_read_that_stops_early_loses_and_repeats_nothing(
    name: str, tail: int, failing: int
) -> None:
    """The fourth page fails the `failing`-th time it is asked for.

    An answer that says a page failed is asked for again, and its lines are
    not kept.

    Args:
        name: The log tool.
        tail: The entries each call asks for.
        failing: Which request for the fourth page fails.
    """
    lines = [f"#{n:06d} " + "w" * 150 for n in range(6000)]
    asked: list[Optional[str]] = []

    def fails(after: Optional[str]) -> bool:
        asked.append(after)
        return after == "3000" and asked.count("3000") == failing

    zenml = _ZenML(_forward_log(lines, fails))
    read: list[str] = []
    retried: set[Optional[str]] = set()

    async def run() -> None:
        async with connected(zenml) as mcp:
            cursor = None
            while True:
                more = {"cursor": cursor} if cursor else {}
                result = await mcp.call_tool(
                    name, {"step_run_id": "s1", "tail": tail, **more}
                )
                assert len(_text_of(result)) <= 40_000
                content = result.structured_content
                part = _messages(content["logs"])
                if "failed to load" in content.get("note", ""):
                    assert content.get("cursor") is None, content["note"]
                    assert not (cursor and part), "a failed read kept lines"
                    assert cursor not in retried
                    retried.add(cursor)
                    continue
                read[:0] = part
                cursor = content.get("cursor")
                if cursor is None:
                    break

    asyncio.run(run())
    assert retried
    assert read == lines


@pytest.mark.parametrize(
    ("name", "tail"),
    [("zenml_get_step_logs", 1000), ("zenml_get_step_log_entries", 1000)],
)
def test_a_log_read_back_to_50000_entries_says_older_ones_cannot_be_read(
    name: str, tail: int
) -> None:
    """A cursor past the newest 50,000 entries is refused, and no page older
    than them is read.

    Args:
        name: The log tool.
        tail: The entries each call asks for.
    """
    lines = [f"#{n:06d}" for n in range(50_500)]
    zenml = _ZenML(_long_log(lines))

    async def run() -> tuple[Any, dict[str, Any]]:
        async with connected(zenml) as mcp:
            refused = await mcp.call_tool(
                name,
                {"step_run_id": "s1", "cursor": _cursor_of({"skip": 50_000})},
            )
            cursor: Optional[str] = _cursor_of({"skip": 49_000})
            content: dict[str, Any] = {}
            while cursor:
                result = await mcp.call_tool(
                    name, {"step_run_id": "s1", "tail": tail, "cursor": cursor}
                )
                content = result.structured_content
                cursor = content.get("cursor")
            return refused, content

    refused, content = asyncio.run(run())
    assert _error(refused)["kind"] == "invalid_request"
    assert (
        "after the newest 50,000 entries of this log, so older entries can't "
        "be read."
        if name == "zenml_get_step_logs"
        else "Entries older than the newest 50,000 can't be read."
    ) in content["note"]
    oldest = min(
        int(before[0])
        for r in zenml.seen
        if (before := r["params"].get("before"))
    )
    assert oldest == 1500, "a page older than the newest 50,000 was read"


@pytest.mark.parametrize("tail", [10, 5000])
def test_a_log_read_stopped_by_its_page_limit_hands_out_no_dead_cursor(
    tail: int,
) -> None:
    """A log store that pages back one entry at a time.

    A call reads at most 100 pages, so the newest 100 lines are all that can
    be read, and no cursor leads nowhere.

    Args:
        tail: The lines each call asks for.
    """
    lines = [f"line {n}" for n in range(300)]
    pages: dict[Optional[str], LogPage] = {
        (str(n) if n < 299 else None): (
            [lines[n]],
            str(n - 1) if n else None,
            None,
        )
        for n in range(300)
    }
    zenml = _ZenML(_log_pages(pages))
    read: list[str] = []

    async def run() -> dict[str, Any]:
        async with connected(zenml) as mcp:
            cursor = None
            while True:
                more = {"cursor": cursor} if cursor else {}
                result = await mcp.call_tool(
                    "zenml_get_step_logs",
                    {"step_run_id": "s1", "tail": tail, **more},
                )
                content: dict[str, Any] = result.structured_content
                assert content["logs"], f"the cursor {cursor} led nowhere"
                read[:0] = content["logs"].split("\n")
                cursor = content["cursor"]
                if cursor is None:
                    return content
                assert "so that call may repeat some lines." in content["note"]

    content = asyncio.run(run())
    assert read == lines[-100:]
    assert content["truncated"] is True
    assert "so older entries can't be read." in content["note"], content


def test_a_line_cut_at_10000_characters_is_reported() -> None:
    """A cut log entry and a cut code line are each reported in the note."""
    code = "a = 1\n" + "b = '" + "x" * 12_000 + "'\nc = 3"
    step = {
        "id": "s1",
        "name": "train",
        "body": {},
        "metadata": {"source_code": code},
        "resources": {
            "log_collection": [{"id": "l1", "body": {"source": "step"}}]
        },
    }
    answers = _long_log(["first", "L" * 30_000, "last"])
    answers["/api/v1/steps/s1"] = lambda _: _json(step)
    zenml = _ZenML(answers)

    async def run() -> tuple[Any, Any]:
        async with connected(zenml) as mcp:
            arguments = {"step_run_id": "s1"}
            entries = await mcp.call_tool(
                "zenml_get_step_log_entries", arguments
            )
            source = await mcp.call_tool("zenml_get_step_code", arguments)
            return entries.structured_content, source.structured_content

    entries, source = asyncio.run(run())
    assert entries["possibly_truncated"] is True
    assert "1 of these entries was cut at 10,000 characters" in entries["note"]
    assert (source["truncated"], source["last_line"]) == (True, 3)
    assert "1 of these lines was cut at 10,000 characters" in source["note"]
    assert "start_line" not in source["note"]


@pytest.mark.parametrize(
    "name", ["zenml_get_step_code", "zenml_get_step_source_code"]
)
@pytest.mark.parametrize("end_line", [None, 2000])
def test_step_code_comes_back_with_its_own_line_endings(
    name: str, end_line: Optional[int]
) -> None:
    """CRLF and a form feed line come back as they are, range by range.

    Args:
        name: The tool.
        end_line: The last line asked for, or None for the end.
    """
    rows = [
        f'    value_{n} = compute({n}, "text")  # line {n}\r\n'
        for n in range(1, 3001)
    ]
    rows[4] = "\x0c\r\n"
    step = {
        "id": "s1",
        "name": "train",
        "body": {},
        "metadata": {"source_code": "".join(rows)},
    }
    zenml = _ZenML({"/api/v1/steps/s1": lambda _: _json(step)})
    arguments: dict[str, Any] = {"step_run_id": "s1", "end_line": end_line}
    parts: list[str] = []

    async def run() -> None:
        async with connected(zenml) as mcp:
            start = 1
            while True:
                result = await mcp.call_tool(
                    name, {**arguments, "start_line": start}
                )
                content = result.structured_content
                assert content["total_lines"] == 3000
                parts.append(content["source_code"])
                if not content["truncated"]:
                    break
                start = content["last_line"] + 1
                assert (
                    f"with the same arguments and start_line={start}."
                    in content["note"]
                )

    asyncio.run(run())
    assert len(parts) > 1
    assert "".join(parts) == "".join(rows[:end_line])


@pytest.mark.parametrize(
    ("key", "credential"),
    [
        ("Authorization", True),
        ("Proxy-Authorization", True),
        ("x_authorization", True),
        ("authorization_mode", False),
        ("exclusive_replacement_authorized", False),
    ],
)
def test_an_authorization_header_is_a_credential(
    key: str, credential: bool
) -> None:
    """A key that ends in `authorization` is masked and refused; one that
    only starts with it, such as a mode, is not.

    Args:
        key: The key.
        credential: Whether it names a credential.
    """
    masked = redact({"headers": {key: "Bearer sample"}})
    assert (masked["headers"][key] == "***") is credential
    assert bool(credential_like_keys({key: "Bearer sample"})) is credential
