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
"""What every ZenML tool shares: targeting, annotations, caches and response shapes."""

from __future__ import annotations

import asyncio
import inspect
import re
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TypeVar
from urllib.parse import quote

import httpx
import pydantic_core
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from zenml_mcp.cache import SingleFlightCache
from zenml_mcp.call import Sensitive
from zenml_mcp.client import (
    ZenMLBadRequest,
    ZenMLNotFound,
    ZenMLRestClient,
    ZenMLRestError,
)
from zenml_mcp.registry import SecretWrites, Tools
from zenml_mcp.resource_spec import MAX_PAGE_SIZE

T = TypeVar("T")

_CACHE_TTL_S = 300.0
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def segment(value: object) -> str:
    """One URL path segment.

    ZenML decodes `%2F` before routing, so a slash is refused rather than
    quoted: no id or name may reach another route.

    Args:
        value: The id or name to put in the path.

    Returns:
        The value, stripped and percent-encoded.

    Raises:
        ZenMLBadRequest: If the value is empty, `.`, `..`, holds a slash or a
            backslash, or is not printable.
    """
    text = str(value).strip()
    if (
        text in {"", ".", ".."}
        or not text.isprintable()
        or any(c in text for c in "/\\")
    ):
        raise ZenMLBadRequest(f"{text!r} is not a valid id or name.")
    return quote(text, safe="")


GATHER_LIMIT = 4


async def gather(*requests: Awaitable[Any]) -> list[Any]:
    """Run requests together, at most `GATHER_LIMIT` at once.

    A failure cancels and awaits the rest; only a shared cache load they
    started finishes for its other waiters.

    Args:
        requests: The awaitables to run.

    Returns:
        Their results, in the order given.

    Raises:
        Exception: The first request's failure, as it was raised.
    """  # noqa: DOC503
    if not requests:
        # `asyncio.wait` refuses an empty set, as a task group would not.
        return []
    slots = asyncio.Semaphore(GATHER_LIMIT)
    tasks = [asyncio.ensure_future(_awaited(r, slots)) for r in requests]
    try:
        # The first failure stops the wait; the rest are then cancelled and
        # awaited, as a task group does (Python 3.10 has none).
        await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in tasks:
            if task.done() and not task.cancelled():
                error = task.exception()
                if error is not None:
                    raise error from None
        return [task.result() for task in tasks]
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def _awaited(request: Awaitable[Any], slots: asyncio.Semaphore) -> Any:
    started = False
    try:
        async with slots:
            started = True
            return await request
    finally:
        if not started and inspect.iscoroutine(request):
            request.close()


# A ZenML read reaches only the caller's own server, so it is a closed world.
ZENML_READ = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def read_tool(
    tools: Tools,
    title: str | None,
    *,
    description: str | None = None,
    needs_server: bool = True,
) -> Callable[..., Any]:
    """Register a read tool.

    A tool ported from mcp-zenml passes no title, as upstream gave none.

    Args:
        tools: Where the tool is registered.
        title: Its title.
        description: Replaces its docstring.
        needs_server: Whether it reads ZenML.

    Returns:
        The decorator that registers it.
    """
    annotations = ZENML_READ.model_copy(update={"title": title})
    return tools.tool(
        description=description,
        annotations=annotations,
        needs_server=needs_server,
    )


def write_tool(
    tools: Tools,
    title: str | None,
    *,
    destructive: bool,
    open_world: bool = False,
    description: str | None = None,
    secret_writes: SecretWrites | None = None,
    sensitive: Sensitive | None = None,
) -> Callable[..., Any]:
    """Register a write tool.

    Args:
        tools: Where the tool is registered.
        title: Its title.
        destructive: Whether it may delete or overwrite.
        open_world: Whether it may reach beyond the ZenML server.
        description: Replaces its docstring.
        secret_writes: The writes a secret page may run.
        sensitive: What the host is asked before every call, if anything.

    Returns:
        The decorator that registers it.
    """
    return tools.tool(
        description=description,
        annotations=ToolAnnotations(
            title=title,
            read_only_hint=False,
            destructive_hint=destructive,
            idempotent_hint=False,
            open_world_hint=open_world,
        ),
        secret_writes=secret_writes,
        sensitive=sensitive,
    )


@dataclass(frozen=True)
class ServerInfo:
    """What a ZenML server says about itself, the same for every caller."""

    url: str
    version: str | None
    is_pro: bool
    dashboard_url: str
    workspace: str | None
    organization: str | None


# Server facts are the same for every caller, so they key on the server URL.
_server_info: SingleFlightCache[ServerInfo] = SingleFlightCache()
# Per-user facts key on the client's `cache_key`, which names the caller and
# the server: one caller never reads another's, and a project the caller
# cannot read stays unreadable.
_default_project: SingleFlightCache[str] = SingleFlightCache()
_project_names: SingleFlightCache[str] = SingleFlightCache()


def _user_key(client: ZenMLRestClient, suffix: str = "") -> str:
    return f"{client.cache_key}\0{suffix}"


async def server_info(client: ZenMLRestClient) -> ServerInfo:
    """The server's version, edition and dashboard, cached per server URL.

    Args:
        client: The client for the server to read.

    Returns:
        The server's info.
    """
    url = client.server_url

    async def load() -> tuple[ServerInfo, float]:
        info = await client.get("/info", what="Reading ZenML server info")
        meta = info.get("metadata") or {}
        dashboard = (
            info.get("dashboard_url") or info.get("server_url") or url
        ).rstrip("/")
        return ServerInfo(
            url=url,
            version=info.get("version"),
            is_pro=info.get("deployment_type") == "cloud",
            dashboard_url=dashboard,
            workspace=info.get("pro_workspace_name")
            or meta.get("workspace_name"),
            organization=info.get("pro_organization_name")
            or meta.get("organization_name"),
        ), _CACHE_TTL_S

    return await _server_info.get(url, load)


async def project(client: ZenMLRestClient, explicit: str | None) -> str:
    """Resolve the project for a project-scoped call.

    ZenML Pro rejects project-scoped lists without a project, and OSS silently
    uses `default`, so always send one: the tool argument, else the client's
    project, else the caller's default project, else their only project,
    else `default`.

    Args:
        client: The caller's client.
        explicit: The project the tool was given, if any.

    Returns:
        The project's name or ID.
    """
    if explicit and explicit.strip():
        return explicit.strip()
    if client.project:
        return client.project

    async def load() -> tuple[str, float]:
        user = await client.get(
            "/current-user", what="Reading the current user"
        )
        default = body_of(user).get("default_project_id")
        if not default:
            # Pro users often have none; with a single project there is no choice.
            projects = await client.get(
                "/projects", params={"size": 2}, what="Listing projects"
            )
            items = projects.get("items") or []
            default = items[0]["id"] if len(items) == 1 else "default"
        return default, _CACHE_TTL_S

    return await _default_project.get(_user_key(client), load)


async def project_name(client: ZenMLRestClient, project_id: str | None) -> str:
    """A project's name for dashboard links, or its ID when it can't be read.

    Args:
        client: The caller's client.
        project_id: The project's ID.

    Returns:
        The project's name, its ID when it can't be read, or `default` without
        an ID.
    """
    if not project_id:
        return "default"

    async def load() -> tuple[str, float]:
        try:
            data = await client.get(
                f"/projects/{segment(project_id)}", what="Reading the project"
            )
        except ZenMLRestError:
            return project_id, 0.0
        return data.get("name") or project_id, _CACHE_TTL_S

    return await _project_names.get(_user_key(client, project_id), load)


def is_uuid(value: str) -> bool:
    """Whether `value` is a UUID, so it names an entity by ID.

    Args:
        value: The id or name to check.

    Returns:
        Whether it is a UUID.
    """
    return bool(_UUID_RE.match(value.strip()))


async def _in_project(
    client: ZenMLRestClient, filters: dict[str, Any]
) -> dict[str, Any]:
    if "project" in filters:
        return {
            **filters,
            "project": await project(client, filters["project"]),
        }
    return filters


async def by_name_or_id(
    client: ZenMLRestClient,
    route: str,
    value: str,
    /,
    *,
    noun: str,
    missing: str,
    hydrate: bool = False,
    id_params: dict[str, Any] | None = None,
    **scope: Any,
) -> dict[str, Any]:
    """One entity by id, else the one named `value`.

    `scope` filters come before the name, and a `project` among them is
    resolved only for a name.

    Args:
        client: The caller's client.
        route: The entity's list route, e.g. `/pipelines`.
        value: The entity's ID or name.
        noun: What the entity is called in request descriptions.
        missing: The message when no entity has that name.
        hydrate: Whether to hydrate the entity found by name.
        id_params: Query parameters for the read by ID.
        scope: Filters for the lookup by name.

    Returns:
        The entity.

    Raises:
        ZenMLNotFound: If no entity has that name.
    """
    if is_uuid(value):
        return await client.get(
            f"{route}/{segment(value)}",
            params=id_params,
            what=f"Reading the {noun}",
        )
    found = await client.get(
        route,
        params={
            **await _in_project(client, scope),
            "name": f"equals:{value.strip()}",
            **({"hydrate": True} if hydrate else {}),
            "size": 1,
        },
        what=f"Finding the {noun}",
    )
    items = found.get("items") or []
    if not items:
        raise ZenMLNotFound(missing)
    return items[0]


def check_page(page: int, size: int) -> None:
    """The generic list tool's `page` and `size` checks, before any request.

    Args:
        page: The page number asked for.
        size: The page size asked for.

    Raises:
        ZenMLBadRequest: If `page` is below 1 or `size` is outside 1 to
            `MAX_PAGE_SIZE`.
    """
    if page < 1:
        raise ZenMLBadRequest(
            "page must be an integer greater than or equal to 1"
        )
    if not 1 <= size <= MAX_PAGE_SIZE:
        raise ZenMLBadRequest(f"size must be between 1 and {MAX_PAGE_SIZE}")


async def list_page(
    client: ZenMLRestClient,
    route: str,
    /,
    *,
    page: int,
    size: int,
    what: str,
    item: Callable[[Any], Any],
    cap: int | None = None,
    **filters: Any,
) -> dict[str, Any]:
    """One page of a list route, each entry shaped by `item` (None drops it).

    `page` and `size` are checked as the generic list tool checks them, before
    any request; `cap` then lowers the size sent. `filters` keep their order.

    Args:
        client: The caller's client.
        route: The list route.
        page: The page number.
        size: The page size.
        what: What the request does, for error messages.
        item: Shapes each entry; None drops it.
        cap: The largest size sent, if any.
        filters: Query filters; a `project` among them is resolved.

    Returns:
        The page, cut to fit in `ANSWER_MAX_CHARS`.
    """
    check_page(page, size)
    data = await client.get(
        route,
        params={
            **await _in_project(client, filters),
            "page": page,
            "size": size if cap is None else min(size, cap),
        },
        what=what,
    )
    shaped = (item(entry) for entry in data.get("items") or [])
    answer = page_of(data, [entry for entry in shaped if entry is not None])
    return fit_page(
        answer, page=page, size=size if cap is None else min(size, cap)
    )


def canonical_uuid(value: str) -> str | None:
    """`value` as a UUID in its canonical form, or None when it is not one.

    Args:
        value: The text to read as a UUID.

    Returns:
        The canonical UUID, or None.
    """
    try:
        return str(uuid.UUID(value))
    except ValueError:
        return None


async def default_project_id(client: ZenMLRestClient) -> str:
    """The ID of the caller's default project, reading it when only named.

    Args:
        client: The caller's client.

    Returns:
        The project's ID.
    """
    chosen = await project(client, None)
    known = canonical_uuid(chosen)
    if known:
        return known
    named = await client.get(
        f"/projects/{segment(chosen)}", what="Reading the default project"
    )
    return str(named["id"])


def utc_naive(value: str) -> datetime:
    """An ISO-8601 time as ZenML stores it: in UTC, without an offset.

    Args:
        value: The ISO-8601 time.

    Returns:
        The time in UTC, without an offset.
    """
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def unknown_outcome(
    tool: str, message: str, details: dict[str, Any]
) -> CallToolResult:
    """mcp-zenml's answer to a call whose response was lost.

    It is an error result that says the outcome is unknown and carries what to
    read to find out.

    Args:
        tool: The tool that was called.
        message: What happened and what to do next.
        details: What to read to find out the outcome.

    Returns:
        The error result.
    """
    error = {
        "tool": tool,
        "message": message,
        "type": "UnknownOutcome",
        "details": details,
    }
    return CallToolResult(
        content=[TextContent(type="text", text=message)],
        structured_content={**details, "error": error},
        is_error=True,
    )


def iso(value: Any) -> str | None:
    """`value` when it is a non-empty string, as ZenML sends times; else None.

    Args:
        value: A time ZenML returned.

    Returns:
        The time, or None.
    """
    return value if isinstance(value, str) and value else None


def seconds_between(start: str | None, end: str | None) -> float | None:
    """Seconds from `start` to `end`, or None when either is missing or unreadable.

    Args:
        start: The ISO-8601 start time.
        end: The ISO-8601 end time.

    Returns:
        The duration in seconds, rounded to one decimal, or None.
    """
    if not start or not end:
        return None
    try:
        delta = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    except ValueError:
        return None
    return round(delta.total_seconds(), 1)


def clip(text: str | None, limit: int) -> tuple[str | None, bool]:
    """`text` cut to `limit` characters plus a marker when it is longer.

    Args:
        text: The text to cut.
        limit: The most characters kept.

    Returns:
        The text, and whether it was cut.
    """
    if text is None or len(text) <= limit:
        return text, False
    return text[:limit] + "\n…[truncated]", True


# The most characters a tool's result may take as the MCP SDK encodes its text
# block. Claude Code moves a result over 50,000 characters to a file, and other
# clients put all of it in the model's context.
ANSWER_MAX_CHARS = 40_000
# The most characters one line or entry may take, so that one always fits.
ITEM_MAX_CHARS = 10_000


def encoded_size(value: Any) -> int:
    """Characters `value` takes in a tool result's text block.

    Args:
        value: The value to measure.

    Returns:
        Its length as indented JSON.
    """
    return len(pydantic_core.to_json(value, fallback=str, indent=2).decode())


def clip_text(text: str, limit: int = ITEM_MAX_CHARS) -> str:
    """`text`, cut so that it encodes to at most `limit` characters.

    Args:
        text: The text to cut.
        limit: The most characters it may encode to.

    Returns:
        The text, cut and marked when it was too long.
    """
    marker = " …[cut]"
    if encoded_size(text) <= limit:
        return text
    # A longer prefix never encodes to fewer characters, so this finds the
    # longest one that fits with the marker.
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if encoded_size(text[:middle] + marker) <= limit:
            low = middle
        else:
            high = middle - 1
    return text[:low] + marker


def fit(
    items: Sequence[T],
    answer: Callable[[Sequence[T]], dict[str, Any]],
    *,
    newest: bool,
) -> tuple[dict[str, Any], int]:
    """The answer built from as many of `items` as fit in `ANSWER_MAX_CHARS`.

    Items are taken from the end with `newest` and from the start otherwise.
    The answer holds at least one, so a reader that follows the answer always
    moves on. Each item must already encode to at most `ITEM_MAX_CHARS`.

    Args:
        items: The items to fit.
        answer: Builds the answer from the items kept.
        newest: Whether to keep the last items rather than the first.

    Returns:
        The answer and how many items it holds.
    """
    room = ANSWER_MAX_CHARS - encoded_size(answer(items[:0]))
    count = used = 0
    for item in reversed(items) if newest else items:
        # An item in a list is indented, and a note grows with the numbers in it.
        used += encoded_size(item) + 16
        if count and used > room - 400:
            break
        count += 1
    while True:
        kept = items[len(items) - count :] if newest else items[:count]
        built = answer(kept)
        size = encoded_size(built)
        if size <= ANSWER_MAX_CHARS or count <= 1:
            return built, count
        count -= max(1, count * (size - ANSWER_MAX_CHARS) // size + 1)


def fit_page(
    answer: dict[str, Any], *, page: int, size: int
) -> dict[str, Any]:
    """A list `answer` of page `page` of `size`, cut to fit in `ANSWER_MAX_CHARS`.

    It keeps the first items that fit, as a number that divides the items
    before this page, so the call in its `next` and note starts at the first
    item left out.

    Args:
        answer: The page's answer, with its `items`.
        page: The page number.
        size: The page size.

    Returns:
        The answer, or a cut one with `truncated`, `next` and `note`.
    """
    if encoded_size(answer) <= ANSWER_MAX_CHARS:
        return answer
    items = answer["items"]
    before = (page - 1) * size

    def cut(kept: Sequence[Any]) -> dict[str, Any]:
        count = len(kept)
        following = {"size": count, "page": before // max(count, 1) + 2}
        return {
            **answer,
            "items": list(kept),
            "truncated": True,
            "next": following,
            "note": f"Only the first {count} of this page's {len(items)} items fit. "
            f"To read on, call again with the same arguments, "
            f"size={following['size']} and page={following['page']}.",
        }

    fitting = fit(items, cut, newest=False)[1]
    if fitting >= len(items):
        return answer
    count = max(c for c in range(1, fitting + 1) if before % c == 0)
    return cut(items[:count])


def name_of(entity: Any) -> str | None:
    """An entity's name, or None when it is not an entity or has no name.

    Args:
        entity: An entity ZenML returned.

    Returns:
        Its name, or None.
    """
    return entity.get("name") if isinstance(entity, dict) else None


def body_of(entity: Any) -> dict[str, Any]:
    """An entity's body, empty when it has none.

    Args:
        entity: An entity ZenML returned.

    Returns:
        Its body.
    """
    body = entity.get("body") if isinstance(entity, dict) else None
    return body if isinstance(body, dict) else {}


def meta_of(entity: Any) -> dict[str, Any]:
    """An entity's metadata, empty when it has none.

    Args:
        entity: An entity ZenML returned.

    Returns:
        Its metadata.
    """
    meta = entity.get("metadata") if isinstance(entity, dict) else None
    return meta if isinstance(meta, dict) else {}


def field_of(entity: Any, field: str) -> Any:
    """A field of an entity ZenML returned, from its body or its metadata.

    Args:
        entity: The entity.
        field: The field's name.

    Returns:
        The field from the body, else the metadata, else the entity itself;
        None when none has it.
    """
    body, metadata = body_of(entity), meta_of(entity)
    if field in body:
        return body[field]
    return metadata.get(field, entity.get(field))


def res_of(entity: Any) -> dict[str, Any]:
    """An entity's resources, empty when it has none.

    Args:
        entity: An entity ZenML returned.

    Returns:
        Its resources.
    """
    res = entity.get("resources") if isinstance(entity, dict) else None
    return res if isinstance(res, dict) else {}


def ref_of(entity: Any) -> dict[str, Any] | None:
    """A nested entity as {id, name}, or None when absent or hidden by RBAC.

    Args:
        entity: The nested entity.

    Returns:
        Its ID and name, or None.
    """
    if not isinstance(entity, dict) or entity.get("permission_denied"):
        return None
    return {"id": entity.get("id"), "name": entity.get("name")}


def page_of(page: dict[str, Any], items: list[Any]) -> dict[str, Any]:
    """A tool's list answer: `items` with the paging of ZenML's `page`.

    Args:
        page: The page ZenML returned.
        items: The shaped entries.

    Returns:
        The items with their page number, page count and total.
    """
    return {
        "items": items,
        "page": page.get("index"),
        "total_pages": page.get("total_pages"),
        "total": page.get("total"),
    }


def answer_lost(error: Exception) -> bool:
    """Whether a request may have reached ZenML and its answer was lost.

    That is a transport failure other than failing to connect, or an answer
    that could not be decoded, as mcp-zenml tells them.

    Args:
        error: The error the request raised.

    Returns:
        Whether the outcome is unknown.
    """
    cause = error.__cause__
    return isinstance(
        cause, httpx.TransportError | httpx.DecodingError
    ) and not (isinstance(cause, httpx.ConnectError | httpx.ConnectTimeout))
