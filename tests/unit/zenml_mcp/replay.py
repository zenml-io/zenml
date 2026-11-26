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
"""Replays recorded mcp-zenml exchanges against the ZenML MCP tools.

Each fixture under `fixtures/` holds cases mcp-zenml (commit `3de0643`)
recorded on the ZenML SDK: a tool's arguments, every request it sent to the
ZenML server with the answer, and its result. A replay answers the same
requests from a fake ZenML server and calls the tool through an in-process
MCP client, so a case passes only when the tool sends the same requests and
returns the same result.
"""

import json
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import httpx
from mcp import Client

from zenml_mcp.call import ZenMLCall
from zenml_mcp.client import BearerToken, ZenMLRestClient
from zenml_mcp.server import build_server

FIXTURES = Path(__file__).parent / "fixtures"
SERVER_URL = "https://zenml.example"

Declared = dict[str, Optional[Callable[[Any], Any]]]
Answer = Callable[[httpx.Request], httpx.Response]
# A case's keys that say how ZenML answered, rather than what was asked.
_ANSWERS = (
    "entity",
    "page",
    "status",
    "detail",
    "lost",
    "text",
    "answer",
    "refused",
    "connect_timeout",
    "undecodable",
    "route_missing",
)


def golden(name: str) -> Any:
    """A recorded fixture.

    Args:
        name: Its file name.

    Returns:
        The fixture.
    """
    return json.loads((FIXTURES / name).read_text())


@asynccontextmanager
async def connected(
    answer: Answer,
    *,
    read_only: bool = False,
    call: Any = None,
    server_url: str = SERVER_URL,
) -> AsyncIterator[Client]:
    """An MCP client of a local server whose ZenML server is `answer`.

    Args:
        answer: Answers each request to the ZenML server.
        read_only: Whether the server offers only read tools.
        call: Builds the `ZenMLCall` from the client, in place of a plain one.
        server_url: The ZenML server's URL.

    Yields:
        The connected MCP client.
    """
    transport = httpx.MockTransport(answer)
    async with httpx.AsyncClient(transport=transport) as http:
        client = ZenMLRestClient(
            server_url,
            BearerToken("token-sample"),
            http=http,
            # Each replay is a caller of its own: the default project is
            # cached per caller.
            cache_key=uuid.uuid4().hex,
        )
        made = call(client) if call else ZenMLCall(client, read_only=read_only)
        server = build_server(made)
        async with Client(server) as mcp:
            yield mcp


async def result_of(
    mcp: Client, name: str, arguments: dict[str, Any], *, resource: bool
) -> tuple[Any, Optional[bool]]:
    """A tool's structured result, or a resource's JSON.

    Args:
        mcp: The client.
        name: The tool's name, or the resource's URI template.
        arguments: The tool's arguments, or the template's values.
        resource: Whether `name` is a resource.

    Returns:
        The content, and whether the tool marked it an error (None for a
        resource).
    """
    if resource:
        read = await mcp.read_resource(name.format(**arguments))
        return json.loads(read.contents[0].text), None  # type: ignore[union-attr]
    result = await mcp.call_tool(name, arguments)
    return result.structured_content, result.is_error


async def replay(
    recorded: dict[str, Any],
    here: Callable[[Any], Any] = lambda result: result,
    *,
    declared: Optional[Declared] = None,
) -> list[tuple[str, Any, Any]]:
    """Run a fixture's cases and return those that differ.

    A case differs when its requests to ZenML or its result differ from the
    recording. The cases recorded for a server without a secret page
    (`local_only`) run too: a local server has none.

    Args:
        recorded: The fixture.
        here: Applies a declared difference to upstream's result first.
        declared: The cases this server answers differently on purpose:
            each with what it does to upstream's result, or None for one
            another test covers.

    Returns:
        The name, requests and result of each case that differs.
    """
    declared = declared or {}
    entities = recorded["entities"]
    script: list[dict[str, Any]] = []
    answered: set[Optional[int]] = set()
    sent: list[dict[str, Any]] = []
    paths = {
        e["path"] for case in recorded["cases"] for e in case["exchanges"]
    }

    def respond(request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/api/v1")
        if path == "/current-user" and not any(
            e["path"] == "/current-user" for e in script
        ):
            # Not recorded: this server's own lookup of the default project.
            body = {"body": {"default_project_id": recorded["project"]}}
            return httpx.Response(200, json=body)
        if path not in paths:
            return httpx.Response(404, json={"detail": "Not Found"})
        raw: dict[str, list[str]] = {}
        for key, value in request.url.params.multi_items():
            raw.setdefault(key, []).append(value)
        asked: dict[str, Any] = {"path": path}
        params = {
            key: values[0] if len(values) == 1 else values
            for key, values in raw.items()
            if values != [recorded["server_defaults"].get(key)]
        }
        if request.method == "GET":
            asked["params"] = params
        else:
            asked["method"] = request.method
            if request.content:
                asked["body"] = json.loads(request.content)
            if params:
                asked["params"] = params
        fitting = [i for i, e in enumerate(script) if e == {**e, **asked}]
        if path == "/flavors" and not fitting:
            # This server's own read, which upstream does not make: a
            # flavor's secret fields, before a component's configuration
            # changes.
            page = {"index": 1, "max_size": 20, "total_pages": 1, "total": 1}
            return httpx.Response(
                200, json={**page, "items": [entities["flavor"]]}
            )
        sent.append(asked)
        # The first matching exchange not answered yet: a request repeated
        # within a case can get another answer the second time.
        index = next((i for i in fitting if i not in answered), None)
        if index is None and fitting:
            index = fitting[0]
        answered.add(index)
        exchange = {"status": 404} if index is None else script[index]
        if exchange.get("refused"):
            raise httpx.ConnectError("refused")
        if exchange.get("connect_timeout"):
            raise httpx.ConnectTimeout("the connection timed out")
        if exchange.get("lost"):
            raise httpx.ReadTimeout("the answer was lost")
        if exchange.get("undecodable"):
            raise httpx.DecodingError("the answer is corrupt")
        if "text" in exchange:
            return httpx.Response(200, text=exchange["text"])
        if "answer" in exchange:
            return httpx.Response(200, json=exchange["answer"])
        if exchange.get("route_missing"):
            return httpx.Response(404, json={"detail": "Not Found"})
        if "status" in exchange:
            detail = exchange.get("detail", ["KeyError", "not found"])
            return httpx.Response(exchange["status"], json={"detail": detail})
        if "entity" in exchange:
            return httpx.Response(200, json=entities[exchange["entity"]])
        if request.method == "DELETE":
            return httpx.Response(204)
        items = [entities[kind] for kind in exchange["page"]]
        if path in {"/service_connector_types", "/tag_resources/batch"}:
            return httpx.Response(200, json=items)
        page = {
            "index": int(raw.get("page", ["1"])[0]),
            "max_size": int(raw.get("size", ["20"])[0]),
            "total_pages": 1,
            "total": len(items),
        }
        return httpx.Response(200, json={**page, "items": items})

    differing = []
    async with connected(respond) as mcp:
        for case in recorded["cases"]:
            if "declared" in case:
                continue
            change = declared.get(case["name"], lambda result: result)
            if change is None:
                continue
            script[:] = case["exchanges"]
            answered.clear()
            sent.clear()
            resource = "resource" in case
            content, is_error = await result_of(
                mcp,
                case["resource"] if resource else case["tool"],
                case["arguments"],
                resource=resource,
            )
            expected = [
                {k: v for k, v in e.items() if k not in _ANSWERS}
                for e in script
            ]
            if "error" in case:
                same = content.get("error", {}).get("kind") == case["error"]
            else:
                same = content == change(here(case["result"]))
            if not resource:
                # Upstream marks a result that carries an error envelope as
                # one.
                result_error = isinstance(
                    case.get("result", {}).get("error"), dict
                )
                same = same and is_error == ("error" in case or result_error)
            if not same or sent != expected:
                differing.append((case["name"], list(sent), content))
    return differing
