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
"""The ZenML MCP tools send and return what mcp-zenml recorded."""

import asyncio
import hashlib
import json
import ssl
from typing import Any

import httpx
import pytest

pytest.importorskip("mcp")

from tests.unit.zenml_mcp.replay import (  # noqa: E402
    Declared,
    connected,
    golden,
    replay,
    result_of,
)
from zenml_mcp.call import ZenMLCall  # noqa: E402
from zenml_mcp.client import (  # noqa: E402
    ZenMLAuth,
    ZenMLAuthError,
    ZenMLRestClient,
    ZenMLUnavailable,
)
from zenml_mcp.resources import projected  # noqa: E402

CATALOG = "resource://zenml_server/resources"
SCHEMA = "resource://zenml_server/resource-schemas/{resource_type}/{operation}"


def test_generic_reads_match_the_standalone_server() -> None:
    """Every resource type, the active user and project, and step logs."""

    async def run() -> list[Any]:
        differing = await replay(golden("generic_read.json"))
        differing += await replay(
            golden("active.json"), declared=_CODE_IN_LINES
        )
        differing += await replay(
            golden("step_logs.json"), declared=_CUT_LOG_ENTRIES
        )
        return differing

    differing = asyncio.run(run())
    assert not differing, differing[0]


# Declared: code comes back as a range of lines, with where it is in the file.
_CODE_IN_LINES: Declared = {
    "get_step_code": lambda result: {
        "source_code": result["result"],
        "first_line": 1,
        "last_line": 1,
        "total_lines": 1,
        "truncated": False,
    }
}


def _older_entries_cursor(result: dict[str, Any]) -> dict[str, Any]:
    """Declared: an answer that leaves older entries out says how to read them.

    It says so in place of upstream's note about `tail`.

    Args:
        result: Upstream's result.

    Returns:
        This server's result.
    """
    cursor = "eyJza2lwIjoyfQ"
    window = (
        "Showing the newest 2 entries. For older entries call again with the "
        f'same arguments and cursor="{cursor}". While the step is running, '
        "new entries shift this window, so that call may repeat some entries."
    )
    note = result["note"].replace(
        "Only the newest 2 of the entries read were returned, because tail=2.",
        "",
    )
    return {**result, "note": f"{note} {window}".strip(), "cursor": cursor}


_CUT_LOG_ENTRIES: Declared = {
    name: _older_entries_cursor
    for name in (
        "the newest entries",
        "a log read newest first stops at tail",
        "a later page that is not JSON",
        "a later page that is rate limited",
    )
}


def test_starting_a_run_sends_what_the_sdk_sends() -> None:
    """A snapshot, a pipeline's newest runnable snapshot and a run template.

    With and without a run configuration, and for a lost or unreadable
    answer. The started run passes through the generic tools' projection,
    which upstream's does not.
    """

    def projected_run(result: dict[str, Any]) -> dict[str, Any]:
        if "pipeline_run" not in result:
            return result
        run = projected(result["pipeline_run"], resource_type="pipeline_run")
        return {**result, "pipeline_run": run}

    differing = asyncio.run(
        replay(golden("trigger_pipeline.json"), projected_run)
    )
    assert not differing, differing[0]


def test_a_stack_the_sdk_would_assert_on_is_refused_as_invalid() -> None:
    """D26: the recorded start, answered as an invalid request."""
    recorded = golden("trigger_pipeline.json")
    cases = [
        {
            **{k: v for k, v in case.items() if k != "declared"},
            "error": "invalid_request",
        }
        for case in recorded["cases"]
        if case.get("declared", "").startswith("D26:")
    ]
    assert len(cases) == 1
    differing = asyncio.run(replay({**recorded, "cases": cases}))
    assert not differing, differing[0]


def test_generic_writes_send_what_the_standalone_server_sends() -> None:
    """Each read, the one write with its body, and the result.

    Secret writes included: without a secret page, the secret in the
    arguments is sent, as mcp-zenml sends it.
    """
    differing = asyncio.run(replay(golden("generic_write.json")))
    assert not differing, differing[0]


def test_a_schedule_update_sends_active_and_concurrency_only_when_named() -> (
    None
):
    """D25: the recorded schedule updates, without the echoed fields.

    ZenML keeps the `active` and `concurrency` an update leaves out, so a
    rename can't undo a change another writer made since the read.
    """
    recorded = golden("generic_write.json")
    cases = []
    for case in recorded["cases"]:
        if not case["name"].startswith("update schedule_trigger:"):
            continue
        named = case["arguments"]["payload"]
        for exchange in case["exchanges"]:
            if exchange.get("method") == "PUT":
                for field in ("active", "concurrency"):
                    if field not in named:
                        del exchange["body"][field]
        cases.append({k: v for k, v in case.items() if k != "declared"})
    assert len(cases) == 4
    differing = asyncio.run(replay({**recorded, "cases": cases}))
    assert not differing, differing[0]


def test_generic_actions_send_what_the_standalone_server_sends() -> None:
    """Each read upstream and the SDK make, the write, and the result."""
    differing = asyncio.run(replay(golden("generic_action.json")))
    assert not differing, differing[0]


def test_most_recent_runs_send_what_the_standalone_server_sends() -> None:
    """The `most_recent_runs` resource, refusals included.

    Its runs pass through the generic tools' projection, which upstream's
    resource does not.
    """

    def projected_page(page: dict[str, Any]) -> dict[str, Any]:
        items = projected(page["items"], resource_type="pipeline_run")
        return {**page, "items": items}

    # Declared: a larger run_count is answered with at most 100 runs.
    declared: Declared = {"more than a ZenML page is refused": None}
    differing = asyncio.run(
        replay(golden("views.json"), projected_page, declared=declared)
    )
    assert not differing, differing[0]


def _digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


@pytest.mark.parametrize("read_only", [False, True])
def test_the_resource_catalog_matches_the_standalone_server(
    read_only: bool,
) -> None:
    """The catalog, through the tool and the catalog resources.

    Describing it reads nothing from ZenML.

    Args:
        read_only: Whether the server offers only read tools.
    """
    seen: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(500)

    async def run() -> list[Any]:
        differing = []
        async with connected(answer, read_only=read_only) as mcp:
            for entry in golden("generic_read.json")["describe"]:
                if (
                    entry.get("read_only", False) != read_only
                    or "mode" in entry
                    or "declared" in entry
                ):
                    continue
                arguments = entry["arguments"]
                reads = [("zenml_describe_resources", False)]
                if not arguments:
                    reads.append((CATALOG, True))
                elif "operation" in arguments:
                    reads.append((SCHEMA, True))
                for name, resource in reads:
                    content, _ = await result_of(
                        mcp, name, arguments, resource=resource
                    )
                    if "error" in entry:
                        error = content.get("error", {})
                        same = error.get("kind") == entry["error"]
                    else:
                        same = _digest(content) == entry["sha256"]
                    if not same:
                        differing.append((name, arguments, content))
        return differing

    differing = asyncio.run(run())
    assert not differing, differing[0]
    assert not seen, "describing the catalog contacted ZenML"


# The server the diagnoses name; the recording's host is replaced by it.
_RECORDED_URL = "https://zenml.example"


class _PasswordLogin(ZenMLAuth):
    """Signs in as the recorded ZenML server's login route expects."""

    def __init__(self, http: httpx.AsyncClient) -> None:
        super().__init__()
        self._http = http

    async def token(self) -> str:
        try:
            response = await self._http.post(
                f"{_RECORDED_URL}/api/v1/login",
                data={"username": "user", "password": "password"},
            )
        except httpx.HTTPError as error:
            raise ZenMLUnavailable(type(error).__name__) from None
        if response.status_code >= 500:
            raise ZenMLUnavailable("the sign-in failed", status=500)
        token = response.json().get("access_token")
        if response.status_code >= 400 or not token:
            raise ZenMLAuthError("the sign-in was refused")
        return str(token)

    async def renew(self, rejected: str) -> str:
        return await self.token()


def _shared(result: dict[str, Any]) -> dict[str, Any]:
    """What both servers report: reachability, version, sign-in and issues.

    Upstream also reports its own process, and names a probe error by its
    own HTTP client.

    Args:
        result: A diagnosis.

    Returns:
        Its shared keys.
    """
    checks = result["checks"]
    connectivity = dict(checks["connectivity"])
    if "last_error_type" in connectivity:
        connectivity["last_error_type"] = "named"
    authentication = {
        key: value
        for key, value in checks["authentication"].items()
        if key in {"attempted", "ok", "failure_kind"}
    }
    version = {
        key: checks[key] for key in ("zenml_server_version",) if key in checks
    }
    return {
        "ok": result["ok"],
        "issues": result["issues"],
        "checks": {
            **version,
            "connectivity": connectivity,
            "authentication": authentication,
        },
    }


def test_setup_diagnosis_reports_what_the_standalone_server_reports() -> None:
    """Reachability, server version, sign-in and issues.

    The sign-in is the client's auth: a refusal it raises as
    `ZenMLAuthError` is rejected, and one it raises as `ZenMLUnavailable` is
    unreachable. Declared cases compare with their recorded `here_result`.
    """

    async def diagnose(case: dict[str, Any]) -> tuple[list[Any], Any]:
        script = {e["path"]: e for e in case["exchanges"]}
        asked: list[dict[str, str]] = []

        def answer(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            asked.append({"method": request.method, "path": path})
            exchange = script[path]
            if exchange.get("refused"):
                raise httpx.ConnectError("refused")
            if exchange.get("untrusted"):
                untrusted = ssl.SSLCertVerificationError(
                    "certificate verify failed"
                )
                raise httpx.ConnectError("certificate verify failed") from (
                    untrusted
                )
            return httpx.Response(exchange["status"], json=exchange["answer"])

        def with_login(client: ZenMLRestClient) -> ZenMLCall:
            client.auth = _PasswordLogin(client.http)
            return ZenMLCall(client)

        async with connected(
            answer, call=with_login, server_url=_RECORDED_URL
        ) as mcp:
            result = await mcp.call_tool("zenml_diagnose_zenml_setup", {})
        return asked, result.structured_content

    differing = []
    for case in golden("diagnose.json")["cases"]:
        asked, content = asyncio.run(diagnose(case))
        expected = [
            {"method": e["method"], "path": e["path"]}
            for e in case["exchanges"]
        ]
        upstream = case.get("here_result", case["result"])
        if asked != expected or _shared(content) != _shared(upstream):
            differing.append((case["name"], asked, content))
        assert "session-sample" not in json.dumps(content)
    assert not differing, differing[0]
