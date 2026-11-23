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
"""Step runs: status, logs and source code.

Two readers follow a step's log stream through the paginated
`/logs/{id}/entries` route of ZenML 0.97+, and fall back to the older
`/steps/{id}/logs` route on a server without it, each with its own stop rules
and notes: `zenml_get_step_logs` answers lines, and
`zenml_get_step_log_entries` is mcp-zenml's `get_step_logs` (`3de0643`), as
`zenml_get_step_source_code` is its `get_step_code`.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from collections.abc import Sequence
from typing import Any

from zenml_mcp.call import ZenMLCall
from zenml_mcp.client import (
    ZenMLAuthError,
    ZenMLBadRequest,
    ZenMLNotFound,
    ZenMLPermissionDenied,
    ZenMLRateLimited,
    ZenMLRestClient,
    ZenMLRestError,
    ZenMLUnsupported,
)
from zenml_mcp.common import (
    ITEM_MAX_CHARS,
    body_of,
    clip_text,
    encoded_size,
    fit,
    iso,
    meta_of,
    name_of,
    read_tool,
    res_of,
    seconds_between,
    segment,
)
from zenml_mcp.credentials import redact
from zenml_mcp.registry import Tools
from zenml_mcp.runs import (
    exception_info,
    metadata_scalars,
    resolve_run,
)

STEP_LOGS_MAX_ENTRIES = 50_000
# Following cursors stops at these limits and returns what it has. They are
# checked between pages, so one more page can pass them. A page that runs into the
# call deadline (`runtime.CALL_TIMEOUT_S`) loses what was read, so the time, counted
# from the start of the call, leaves room for it. Cancelling a page instead could
# cancel a login. The pod is shared and its memory is limited (1536Mi in the
# deployed values), so the characters are limited too.
STEP_LOGS_MAX_PAGES = 100
STEP_LOGS_MAX_READ_CHARS = 20_000_000
STEP_LOGS_READ_BUDGET_S = 60.0
STEP_LOGS_DEFAULT_TAIL = 200
STEP_LOGS_MAX_LINES = 5000
STEP_LOG_ENTRIES_MAX_TAIL = 1000
logger = logging.getLogger("zenml_mcp")

_LOG_LEVELS = {
    10: "DEBUG",
    20: "INFO",
    30: "WARNING",
    40: "ERROR",
    50: "CRITICAL",
}

# Server URLs that answered `/logs/{id}/entries` with FastAPI's "no such
# route", with the time of that answer: for an hour, calls go straight to the
# older route. A fact about the server, the same for every caller.
_servers_without_log_entries: dict[str, float] = {}
_LOG_ENTRIES_RECHECK_S = 3600.0


# Errors whose HTTP status their class tells, named as upstream names them.
_STATUS_OF = {
    ZenMLPermissionDenied: 403,
    ZenMLNotFound: 404,
    ZenMLRateLimited: 429,
}


def _step_source(step: dict[str, Any]) -> tuple[str | None, str | None]:
    """A step's import path and module, from `metadata.spec.source`.

    Args:
        step: The step run.

    Returns:
        The import path and the module, each None when unknown.
    """
    source = (meta_of(step).get("spec") or {}).get("source")
    if isinstance(source, dict):
        module, attribute = source.get("module"), source.get("attribute")
        return (
            f"{module}.{attribute}" if module and attribute else attribute
        ), module
    if isinstance(source, str):
        return source, source.rpartition(".")[0] or None
    return None, None


def _local_step_logs(
    step: dict[str, Any], logs_uri: str | None
) -> dict[str, Any]:
    """The answer for a step that ran on a stack with a local artifact store.

    The logs are files on the machine that ran it, out of the server's reach.

    Args:
        step: The step run.
        logs_uri: Where the logs are on the machine that ran the step.

    Returns:
        A log answer with no lines and a note saying where they are.
    """
    return {
        "step_run_id": step.get("id"),
        "step": step.get("name"),
        "status": body_of(step).get("status"),
        "logs": "",
        "local_logs_uri": logs_uri,
        "note": "This step's logs are stored in a local artifact store, "
        "so the ZenML server cannot read them, and neither can this server. "
        "They are files at local_logs_uri on the machine that ran the pipeline.",
    }


async def _resolve_step(
    client: ZenMLRestClient,
    step_run_id: str | None,
    run: str | None,
    step_name: str | None,
    project: str | None,
) -> dict[str, Any]:
    if step_run_id:
        return await client.get(
            f"/steps/{segment(step_run_id)}", what="Reading the step"
        )
    if not (run and step_name):
        raise ZenMLBadRequest("Pass step_run_id, or both run and step_name.")
    data = await resolve_run(client, run, project)
    steps = await client.get(
        "/steps",
        params={
            "project": body_of(data).get("project_id"),
            "pipeline_run_id": data["id"],
            "name": f"equals:{step_name}",
            "exclude_retried": True,
            "size": 1,
        },
        what="Finding the step",
    )
    items = steps.get("items") or []
    if not items:
        raise ZenMLNotFound(
            f"Run {data.get('name')!r} has no step {step_name!r}."
        )
    return await client.get(
        f"/steps/{segment(items[0]['id'])}", what="Reading the step"
    )


def _artifacts(group: Any) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for name, versions in (group or {}).items():
        items = versions if isinstance(versions, list) else [versions]
        out[name] = [
            {
                "artifact_version_id": v.get("id"),
                "artifact": name_of(body_of(v).get("artifact")),
                "version": body_of(v).get("version"),
                "type": body_of(v).get("type"),
            }
            for v in items
            if isinstance(v, dict) and not v.get("permission_denied")
        ]
    return out


def _cursor(skip: int) -> str:
    """Where the next older part of a log starts.

    It counts the lines or entries newer than it, from the newest. It holds
    nothing else, so it can't name another step, workspace or backend route.

    Args:
        skip: How many of the newest lines or entries come before it.

    Returns:
        The cursor.
    """
    raw = json.dumps({"skip": skip}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _next_cursor(skip: int, shown: int, older_left: bool) -> str | None:
    """The cursor past what an answer shows.

    There is one only when there may be more to read and the log store can
    reach it.

    Args:
        skip: How many of the newest lines or entries the answer skipped.
        shown: How many the answer shows.
        older_left: Whether older lines or entries may exist.

    Returns:
        The cursor, or None when there is nothing more to read.
    """
    position = skip + shown
    if shown and older_left and position < STEP_LOGS_MAX_ENTRIES:
        return _cursor(position)
    return None


def _skip_of(cursor: str | None) -> int:
    if cursor is None:
        return 0
    refused = ZenMLBadRequest(
        "cursor is not one this tool returned; call again without it."
    )
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", cursor):
        raise refused
    try:
        data = json.loads(
            base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        )
    except ValueError as error:
        raise refused from error
    skip = (
        data.get("skip")
        if isinstance(data, dict) and data.keys() == {"skip"}
        else None
    )
    if type(skip) is not int or not 1 <= skip < STEP_LOGS_MAX_ENTRIES:
        raise refused
    return skip


def _window_note(
    unit: str,
    shown: int,
    skip: int,
    total: int | None,
    cursor: str | None,
    older_left: bool,
) -> str:
    """The sentence a cut log answer ends with: what it shows and how to read on.

    Args:
        unit: What the log holds, `lines` or `entries`.
        shown: How many the answer shows.
        skip: How many of the newest it skipped.
        total: How many there are, or None when unknown.
        cursor: The cursor to read on from, if any.
        older_left: Whether older ones may exist.

    Returns:
        The note.
    """
    where = (
        f"{shown:,} {unit} before the newest {skip:,}"
        if skip
        else f"the newest {shown:,} {unit}"
    )
    of = "" if total is None else f" of {total:,}"
    note = f"Showing {where}{of}."
    if cursor:
        note += (
            f" For older {unit} call again with the same arguments and "
            f'cursor="{cursor}". While the step is running, new {unit} shift '
            f"this window, so that call may repeat some {unit}."
        )
    elif shown and older_left:
        note += (
            f" {unit.capitalize()} older than the newest "
            f"{STEP_LOGS_MAX_ENTRIES:,} can't be read."
        )
    elif not shown:
        note += f" No older {unit} can be read."
    return note


def _unplaced_note(unit: str) -> str:
    """Why an answer read from a cursor shows nothing.

    The read stopped before the newest entry, or a page failed, so where the
    cursor points is unknown.

    Args:
        unit: What the log holds, `lines` or `entries`.

    Returns:
        The note.
    """
    return (
        f"No {unit} are shown, as reading stopped early and the {unit} this "
        "cursor points to can't be found. Call again with the same arguments "
        "and cursor to read them."
    )


def _clipped_note(count: int, unit: str) -> str:
    were, them = ("was", "it") if count == 1 else ("were", "them")
    return (
        f"{count:,} of these {unit} {were} cut at {ITEM_MAX_CHARS:,} characters, "
        f"and the rest of {them} can't be read through this tool."
    )


def _clipped_entry(entry: Any) -> Any:
    """A log entry that encodes to at most `ITEM_MAX_CHARS`, its message cut.

    Args:
        entry: The log entry.

    Returns:
        The entry as it is when it fits; otherwise with its message cut, or
        as cut text when its message can't be cut.
    """
    if encoded_size(entry) <= ITEM_MAX_CHARS:
        return entry
    if isinstance(entry, dict) and isinstance(entry.get("message"), str):
        room = ITEM_MAX_CHARS - encoded_size({**entry, "message": ""})
        if room > 100:
            return {**entry, "message": clip_text(entry["message"], room)}
    return clip_text(str(entry))


def _log_line(entry: Any) -> str:
    if not isinstance(entry, dict):
        return str(entry)
    stamp = (entry.get("timestamp") or "")[11:19]
    level = entry.get("level")
    level_name = (
        _LOG_LEVELS.get(level, str(level))
        if isinstance(level, int)
        else str(level)
        if level is not None
        else ""
    )
    return f"{stamp} {level_name} {entry.get('message', '')}".strip()


def _logs_limit_note() -> str:
    return (
        f"The log store returned its limit of {STEP_LOGS_MAX_ENTRIES} entries, "
        "counted from the start, so later entries may be missing."
    )


async def _read_log_entries(
    client: ZenMLRestClient,
    logs_id: str,
    *,
    wanted: int,
    contains: str | None,
    deadline: float,
) -> tuple[list[Any], str | None, bool, bool, bool]:
    """A log stream's entries, oldest first, and how reading them went.

    The first request lets each log store start from its own end: the artifact
    store has no cursors, Datadog starts at the newest entry. `before` pages hold
    older entries and `after` pages newer ones. Walking back stops once `wanted`
    matching lines are in hand; walking forward keeps going, as the tail is last.

    Args:
        client: The client to read with.
        logs_id: The log stream's ID.
        wanted: How many matching lines a walk back needs before it stops.
        contains: Text a line must hold to count toward `wanted`, if any.
        deadline: The `time.monotonic()` time after which no page is asked for.

    Returns:
        The entries, oldest first; why reading stopped early, if it did;
        whether no older entry can be read; whether the newest entry was
        reached; and whether a page failed to load.

    Raises:
        TypeError: When a later page's items are not a list. It is caught here
            and ends paging with a note.
        ZenMLAuthError: When the server refuses the credentials for a later
            page, rather than answering with a partial read.
    """
    path = f"/logs/{segment(logs_id)}/entries"
    page = await client.get(
        path, params={"limit": STEP_LOGS_MAX_ENTRIES}, what="Reading step logs"
    )
    pages = [list(page.get("items") or [])]
    direction = "before" if page.get("before") else "after"
    cursor = page.get(direction)
    if not cursor:
        full = len(pages[0]) >= STEP_LOGS_MAX_ENTRIES
        return (
            pages[0],
            _logs_limit_note() if full else None,
            True,
            True,
            False,
        )

    needle = contains.lower() if contains else ""
    total = chars = matches = 0

    def count(items: list[Any]) -> None:
        nonlocal total, chars, matches
        lines = [_log_line(item) for item in items]
        total += len(lines)
        chars += sum(map(len, lines))
        matches += sum(needle in line.lower() for line in lines)

    count(pages[0])
    walking_back = direction == "before"
    unread = "older" if walking_back else "newer"
    note = None
    failed = stuck = False
    while (
        cursor
        and total < STEP_LOGS_MAX_ENTRIES
        and chars < STEP_LOGS_MAX_READ_CHARS
        and len(pages) < STEP_LOGS_MAX_PAGES
        and time.monotonic() < deadline
        and not (walking_back and matches >= wanted)
    ):
        try:
            page = await client.get(
                path, params={direction: cursor}, what="Reading step logs"
            )
            items = page.get("items") or []
            if not isinstance(items, list):
                raise TypeError("log page has no list of items")
            count(items)
        except ZenMLAuthError:
            raise
        except (
            AttributeError,
            ZenMLRestError,
            TimeoutError,
            TypeError,
            ValueError,
        ) as error:
            # Keep what was read rather than lose it to a rate limit or an outage.
            logger.warning(
                "Stopped paging step logs: %s", type(error).__name__
            )
            note = (
                f"A later page of logs failed to load ({type(error).__name__}), "
                f"so {unread} entries are missing. Calling again may return them."
            )
            failed = True
            break
        pages.append(items)
        previous, cursor = cursor, page.get(direction)
        if cursor == previous:
            # Following it would repeat the page and invent duplicate lines.
            note = f"The log store repeated a cursor, so {unread} entries may be missing."
            stuck = True
            break
    # A walk back stopped by a limit, or by a repeated cursor, stops at the same
    # entry on every call, so nothing older than what it read can be reached.
    limited = bool(cursor) and (
        stuck
        or total >= STEP_LOGS_MAX_ENTRIES
        or chars >= STEP_LOGS_MAX_READ_CHARS
        or len(pages) >= STEP_LOGS_MAX_PAGES
        or (time.monotonic() >= deadline and matches < wanted)
    )
    if walking_back and limited and note is None:
        note = (
            f"Reading stops at this tool's limits after the newest {total:,} "
            "entries of this log, so older entries can't be read."
        )
    elif cursor and note is None and not (walking_back and matches >= wanted):
        note = f"Reading stopped after {total} entries; {unread} entries were not read."
    if walking_back:
        pages.reverse()
    entries = [entry for items in pages for entry in items]
    return (
        entries,
        note,
        not (walking_back and cursor) or (limited and not failed),
        walking_back or not cursor,
        failed,
    )


async def _step_log_entries(
    client: ZenMLRestClient,
    step: dict[str, Any],
    logs_id: str | None,
    *,
    wanted: int,
    contains: str | None,
    deadline: float,
) -> tuple[list[Any], str | None, bool, bool, bool]:
    """A step's log entries and how reading them went.

    They come from the log entries route, or the step's own logs route on a
    server without it.

    Args:
        client: The client to read with.
        step: The step run.
        logs_id: The step's log stream ID, if it has one.
        wanted: How many matching lines a walk back needs before it stops.
        contains: Text a line must hold to count toward `wanted`, if any.
        deadline: The `time.monotonic()` time after which no page is asked for.

    Returns:
        The entries, oldest first; what is missing from them; whether no older
        entry can be read; whether the newest was reached; and whether a page
        failed.

    Raises:
        ZenMLNotFound: When the log stream is missing on a server that has
            the log entries route.
    """
    if logs_id:
        try:
            return await _read_log_entries(
                client,
                logs_id,
                wanted=wanted,
                contains=contains,
                deadline=deadline,
            )
        except ZenMLNotFound as error:
            if not error.route_missing:
                raise
    try:
        data = await client.get(
            f"/steps/{segment(step['id'])}/logs",
            params={"source": "step"},
            what="Reading step logs",
        )
    except ZenMLNotFound:
        return [], None, True, True, False
    entries = list(data or [])
    note = (
        _logs_limit_note() if len(entries) >= STEP_LOGS_MAX_ENTRIES else None
    )
    return entries, note, True, True, False


def _page_failure(error: Exception) -> str:
    """How upstream names a later page that failed.

    It is the page's HTTP status, or the error's type. Statuses this server's
    errors share are named by type.

    Args:
        error: The error the page failed with.

    Returns:
        `HTTP <status>`, or the name of the error's type or its cause's.
    """
    status = next(
        (s for kind, s in _STATUS_OF.items() if isinstance(error, kind)), None
    )
    if status is not None:
        return f"HTTP {status}"
    return type(error.__cause__ or error).__name__


def _entries_limit_note() -> str:
    return (
        f"The log store returns only the first {STEP_LOGS_MAX_ENTRIES:,} entries "
        "of a log, counted from the start, so later entries are missing."
    )


async def _stream_id(
    client: ZenMLRestClient, step_id: str, source: str
) -> str | None:
    step = await client.get(
        f"/steps/{segment(step_id)}",
        params={"hydrate": True},
        what="Reading the step",
    )
    for logs in (step.get("resources") or {}).get("log_collection") or []:
        if (logs.get("body") or {}).get("source") == source:
            return logs.get("id")
    return None


async def _entries_as_upstream(
    client: ZenMLRestClient, logs_id: str, wanted: int
) -> tuple[list[Any], bool, str | None, bool, bool, bool] | None:
    """A log stream's entries, read as upstream reads them.

    Args:
        client: The client to read with.
        logs_id: The log stream's ID.
        wanted: How many of the newest entries a walk back needs.

    Returns:
        `(entries, more may exist, note, older may exist, newest read, a page
        failed)`, or None on a server without the route.

    Raises:
        ZenMLAuthError: When the server refuses the credentials for a later
            page, rather than answering with a partial read.
        ZenMLNotFound: When the log stream is missing on a server that has
            the route.
    """
    path = f"/logs/{segment(logs_id)}/entries"
    try:
        page = await client.get(
            path,
            params={"limit": STEP_LOGS_MAX_ENTRIES},
            what="Reading step logs",
        )
    except ZenMLNotFound as error:
        if error.route_missing:
            return None
        raise
    pages: list[list[Any]] = [page.get("items") or []]
    direction = "before" if page.get("before") else "after"
    cursor = page.get(direction)
    if not cursor:
        full = len(pages[0]) >= STEP_LOGS_MAX_ENTRIES
        note = _entries_limit_note() if full else None
        return pages[0], full, note, False, True, False
    walking_back = direction == "before"
    stop_at = (
        min(wanted, STEP_LOGS_MAX_ENTRIES)
        if walking_back
        else STEP_LOGS_MAX_ENTRIES
    )
    unread = "older" if walking_back else "newer"
    total = len(pages[0])
    note = None
    failed = False
    while cursor and total < stop_at:
        try:
            page = await client.get(
                path, params={direction: cursor}, what="Reading step logs"
            )
        except ZenMLAuthError:
            raise
        except (ZenMLRestError, ValueError) as error:
            # Keep the pages already read rather than discarding them.
            failure = _page_failure(error)
            note = (
                f"A later page of logs failed to load ({failure}), so {unread} "
                "entries are missing. Calling again may return them."
            )
            failed = True
            break
        items = page.get("items") or []
        if not items:
            cursor = None
            break
        pages.append(items)
        total += len(items)
        cursor = page.get(direction)
    if cursor and note is None and not walking_back:
        note = (
            f"Reading stopped at the {STEP_LOGS_MAX_ENTRIES:,}-entry limit, so "
            f"{unread} entries were not read."
        )
    if walking_back:
        pages.reverse()
    entries = [entry for items in pages for entry in items]
    newest = walking_back or not cursor
    return (
        entries,
        bool(cursor),
        note,
        walking_back and bool(cursor),
        newest,
        failed,
    )


async def _log_entries_answer(
    client: ZenMLRestClient,
    step_id: str,
    source: str | None,
    logs_id: str | None,
    tail: int,
    skip: int,
) -> dict[str, Any]:
    wanted = skip + tail
    server = client.server_url
    fetched = None
    marked_old_at = _servers_without_log_entries.get(server)
    if (
        marked_old_at is None
        or time.monotonic() - marked_old_at >= _LOG_ENTRIES_RECHECK_S
    ):
        stream = logs_id or await _stream_id(client, step_id, str(source))
        # No stream with that source: the older route answers ZenML's usual
        # "no logs found" error.
        if stream is not None:
            fetched = await _entries_as_upstream(client, stream, wanted)
            if fetched is None:
                _servers_without_log_entries[server] = time.monotonic()
            else:
                _servers_without_log_entries.pop(server, None)
    if fetched is None:
        params: dict[str, str | None] = (
            {"source": source} if source is not None else {"logs_id": logs_id}
        )
        data = await client.get(
            f"/steps/{segment(step_id)}/logs",
            params=params,
            what="Reading step logs",
        )
        if not isinstance(data, list):
            return data
        full = len(data) >= STEP_LOGS_MAX_ENTRIES
        note = _entries_limit_note() if full else None
        fetched = data, full, note, False, True, False
    entries, more, note, older_unread, newest, failed = fetched
    unplaced = bool(skip) and (failed or not newest)
    older = [] if unplaced else entries[: max(0, len(entries) - skip)]
    asked = older[-tail:]
    clipped_entries = [_clipped_entry(entry) for entry in asked]
    cut = [
        kept is not entry
        for kept, entry in zip(clipped_entries, asked, strict=True)
    ]

    def answer(kept: Sequence[Any]) -> dict[str, Any]:
        rest = len(older) > len(kept) or older_unread
        cursor = _next_cursor(skip, len(kept), rest) if newest else None
        clipped = sum(cut[len(cut) - len(kept) :])
        notes = [note] if note else []
        if unplaced:
            notes.append(_unplaced_note("entries"))
        elif cursor or skip:
            notes.append(
                _window_note("entries", len(kept), skip, None, cursor, rest)
            )
        if clipped:
            notes.append(_clipped_note(clipped, "entries"))
        result: dict[str, Any] = {
            "logs": list(kept),
            "possibly_truncated": more
            or len(kept) < len(entries)
            or bool(clipped),
        }
        if notes:
            result["note"] = " ".join(notes)
        if cursor:
            result["cursor"] = cursor
        return result

    return fit(clipped_entries, answer, newest=True)[0]


def _code_lines(
    code: str, start_line: int, end_line: int | None, frame: dict[str, Any]
) -> dict[str, Any]:
    """`frame` with lines `start_line` to `end_line` of `code`, as many as fit.

    A line ends at a newline and keeps it, so the parts join back to `code`.

    Args:
        code: The source code.
        start_line: The first line to return, from 1.
        end_line: The last line to return, or None for the end of the code.
        frame: The fields the answer carries besides the code.

    Returns:
        The answer, with a note on how to read on when it is cut.

    Raises:
        ZenMLBadRequest: When the line range is invalid or starts past the
            end of the code.
    """
    if start_line < 1 or (end_line is not None and end_line < start_line):
        raise ZenMLBadRequest(
            "start_line must be at least 1, and end_line at least start_line."
        )
    lines = re.findall(r"[^\n]*\n|[^\n]+\Z", code)
    total = len(lines)
    if start_line > max(total, 1):
        raise ZenMLBadRequest(
            f"start_line is past the end: the code has {total} lines."
        )
    stop = total if end_line is None else min(end_line, total)
    asked = lines[start_line - 1 : stop]
    wanted = []
    for line in asked:
        text = line.removesuffix("\n")
        wanted.append(clip_text(text) + line[len(text) :])
    cut = [kept != line for kept, line in zip(wanted, asked, strict=True)]

    def answer(kept: Sequence[str]) -> dict[str, Any]:
        last = start_line - 1 + len(kept)
        clipped = sum(cut[: len(kept)])
        result = {
            **frame,
            "source_code": "".join(kept),
            "first_line": start_line,
            "last_line": last,
            "total_lines": total,
            "truncated": last < stop or bool(clipped),
        }
        notes = []
        if last < stop:
            notes.append(
                f"Showing lines {start_line:,}-{last:,} of {total:,}. For the rest "
                f"call again with the same arguments and start_line={last + 1}."
            )
        if clipped:
            notes.append(_clipped_note(clipped, "lines"))
        if notes:
            result["note"] = " ".join(notes)
        return result

    return fit(wanted, answer, newest=False)[0]


def register(tools: Tools) -> None:
    """Register the tools that read a step run, its logs and its code.

    Args:
        tools: Where the tools are registered.
    """

    @read_tool(tools, "Get a step run")
    async def zenml_get_step_run(
        call: ZenMLCall,
        step_run_id: str | None = None,
        run: str | None = None,
        step_name: str | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        """Get one step of a pipeline run: status, timing, parameters, cache use, inputs, outputs and error.

        Identify the step by `step_run_id`, or by `run` (ID or name) plus `step_name`.
        """  # noqa: DOC101, DOC103, DOC201
        client = call.client
        step = await _resolve_step(
            client, step_run_id, run, step_name, project
        )
        body, meta, res = body_of(step), meta_of(step), res_of(step)
        config = meta.get("config") or {}
        start, end = iso(body.get("start_time")), iso(body.get("end_time"))
        return {
            "id": step.get("id"),
            "name": step.get("name"),
            "status": body.get("status"),
            "start_time": start,
            "end_time": end,
            "duration_seconds": seconds_between(start, end),
            "pipeline_run_id": meta.get("pipeline_run_id"),
            "parameters": redact(config.get("parameters")),
            "enable_cache": config.get("enable_cache"),
            "cached_from_step_run_id": meta.get("original_step_run_id"),
            "upstream_steps": (meta.get("spec") or {}).get("upstream_steps"),
            "source": _step_source(step)[0],
            "docstring": meta.get("docstring"),
            "inputs": _artifacts(res.get("inputs")),
            "outputs": _artifacts(res.get("outputs")),
            "exception": exception_info(meta.get("exception_info")),
            "retry_attempt": body.get("version"),
            "metadata": metadata_scalars(meta.get("run_metadata")),
        }

    @read_tool(tools, "Read step logs")
    async def zenml_get_step_logs(
        call: ZenMLCall,
        step_run_id: str | None = None,
        run: str | None = None,
        step_name: str | None = None,
        tail: int = STEP_LOGS_DEFAULT_TAIL,
        contains: str | None = None,
        cursor: str | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        """Read the logs a step printed, newest lines last.

        Returns the last `tail` lines (default 200, max 5000), as many as fit in
        40,000 characters; `contains` keeps only lines with that text
        (case-insensitive). A cut answer returns a `cursor`: pass it with the
        same arguments to read the lines before it. Identify the step by
        `step_run_id`, or by `run` plus `step_name`.
        """  # noqa: DOC101, DOC103, DOC201, DOC501, DOC503
        deadline = time.monotonic() + STEP_LOGS_READ_BUDGET_S
        skip = _skip_of(cursor)
        client = call.client
        step = await _resolve_step(
            client, step_run_id, run, step_name, project
        )
        tail = max(1, min(int(tail), STEP_LOGS_MAX_LINES))
        log_entry = next(
            (
                entry
                for entry in res_of(step).get("log_collection") or []
                if body_of(entry).get("source") == "step"
            ),
            None,
        )
        logs_id = log_entry.get("id") if log_entry else None
        logs_uri = body_of(log_entry).get("uri") if log_entry else None
        try:
            (
                entries,
                note,
                at_oldest,
                reached_newest,
                failed,
            ) = await _step_log_entries(
                client,
                step,
                logs_id,
                wanted=skip + tail,
                contains=contains,
                deadline=deadline,
            )
        except ZenMLPermissionDenied as error:
            # Servers without the log entries route raise the same error from
            # the step's logs route.
            if "local artifact store" not in error.message:
                raise
            return _local_step_logs(step, logs_uri)
        lines = [_log_line(entry) for entry in entries]
        if contains:
            needle = contains.lower()
            lines = [line for line in lines if needle in line.lower()]
        total = len(lines) if at_oldest and note is None else None
        unplaced = bool(skip) and (failed or not reached_newest)
        older = [] if unplaced else lines[: max(0, len(lines) - skip)]
        asked = older[-tail:]
        wanted = [clip_text(line) for line in asked]
        cut = [kept != line for kept, line in zip(wanted, asked, strict=True)]

        def answer(kept: Sequence[str]) -> dict[str, Any]:
            rest = len(older) > len(kept) or not at_oldest
            more = (
                _next_cursor(skip, len(kept), rest) if reached_newest else None
            )
            clipped = sum(cut[len(cut) - len(kept) :])
            notes = [note] if note else []
            if unplaced:
                notes.append(_unplaced_note("lines"))
            elif more or skip:
                notes.append(
                    _window_note("lines", len(kept), skip, total, more, rest)
                )
            elif not entries and not note:
                notes.append(
                    "No logs are stored for this step (it may not have started, "
                    "or step logs are disabled or not retained)."
                )
            if clipped:
                notes.append(_clipped_note(clipped, "lines"))
            return {
                "step_run_id": step.get("id"),
                "step": step.get("name"),
                "status": body_of(step).get("status"),
                "total_lines": total,
                "shown_lines": len(kept),
                "logs": "\n".join(kept),
                "truncated": bool(more or skip or note or clipped),
                "cursor": more,
                "note": " ".join(notes) or None,
            }

        return fit(wanted, answer, newest=True)[0]

    @read_tool(tools, "Read step source code")
    async def zenml_get_step_code(
        call: ZenMLCall,
        step_run_id: str | None = None,
        run: str | None = None,
        step_name: str | None = None,
        start_line: int = 1,
        end_line: int | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        """Get the source code a step ran with, its import path and code hash.

        Returns lines `start_line` to `end_line` (1-based, default the whole
        code), as many as fit in 40,000 characters, with `total_lines`; a cut
        answer names the `start_line` to read on from. The step's exception
        `user_code_line` is the failing line's offset into this source (0 is
        line 1); the traceback has the file's line number. Use them to find the
        failing line.
        """  # noqa: DOC101, DOC103, DOC201
        client = call.client
        step = await _resolve_step(
            client, step_run_id, run, step_name, project
        )
        meta = meta_of(step)
        source, module = _step_source(step)
        frame = {
            "step_run_id": step.get("id"),
            "step": step.get("name"),
            "source": source,
            "module": module,
            "code_hash": meta.get("code_hash"),
        }
        code = meta.get("source_code")
        if code is None:
            return {**frame, "source_code": None, "truncated": False}
        return _code_lines(str(code), start_line, end_line, frame)


# mcp-zenml's description of `get_step_logs`, with this server's limits.
_GET_STEP_LOG_ENTRIES = """Get the logs for a specific step run.

    Returns ``{"logs": [...], "possibly_truncated": bool}`` with entries oldest
    first: the newest 200 entries, or ``tail`` of them, as many as fit in 40,000
    characters. ``possibly_truncated`` is true when the step may have more log
    entries than were returned, or an entry's message was cut at 10,000
    characters, and a ``note`` then says which entries are missing or cut and
    why. When older entries can be read, the answer has a
    ``cursor``: pass it with the same arguments to get the entries before
    these. Log stores that can only read a log from its start (the default
    artifact store) return the newest of the first 50,000 entries for a longer
    log, with ``possibly_truncated`` set.

    Args:
        step_run_id: The ID of the step run to get logs for.
        source: Optional log source. Defaults to ZenML's ordinary ``step`` source.
        logs_id: Optional exact log record ID. Cannot be combined with ``source``.
        tail: Optional number of newest entries to return, from 1 to 1000.
        cursor: Optional ``cursor`` of an earlier answer, to read older entries.
    """


# mcp-zenml's description of `get_step_code`, with this server's line ranges.
_GET_STEP_SOURCE_CODE = """Get the code for a step.

    Returns lines ``start_line`` to ``end_line`` (1-based, default the whole
    code), as many as fit in 40,000 characters, with ``total_lines``. A cut
    answer has a ``note`` naming the ``start_line`` to read on from.

    Args:
        step_run_id: The ID of the step to retrieve
        start_line: First line to return, from 1.
        end_line: Optional last line to return.
    """


def register_entries_and_source(tools: Tools) -> None:
    """Register mcp-zenml's step log entries and step source code tools.

    Args:
        tools: Where the tools are registered.
    """

    @read_tool(tools, None, description=_GET_STEP_LOG_ENTRIES)
    async def zenml_get_step_log_entries(
        call: ZenMLCall,
        step_run_id: str,
        source: str | None = None,
        logs_id: str | None = None,
        tail: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        if source is not None:
            source = source.strip()
            if not source:
                raise ZenMLBadRequest("source must be a non-empty string.")
        if logs_id is not None:
            logs_id = logs_id.strip()
            if not logs_id:
                raise ZenMLBadRequest("logs_id must be a non-empty string.")
        if source is not None and logs_id is not None:
            raise ZenMLBadRequest(
                "Only one of source or logs_id may be provided."
            )
        if source is None and logs_id is None:
            source = "step"
        if tail is not None and not 1 <= tail <= STEP_LOG_ENTRIES_MAX_TAIL:
            raise ZenMLBadRequest(
                f"tail must be between 1 and {STEP_LOG_ENTRIES_MAX_TAIL}."
            )
        skip = _skip_of(cursor)
        client = call.client
        return await _log_entries_answer(
            client,
            step_run_id,
            source,
            logs_id,
            tail or STEP_LOGS_DEFAULT_TAIL,
            skip,
        )

    @read_tool(tools, None, description=_GET_STEP_SOURCE_CODE)
    async def zenml_get_step_source_code(
        call: ZenMLCall,
        step_run_id: str,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> dict[str, Any]:
        client = call.client
        step = await client.get(
            f"/steps/{segment(step_run_id)}",
            params={"hydrate": True},
            what="Reading the step",
        )
        code = (step.get("metadata") or {}).get("source_code")
        if code is None:
            raise ZenMLUnsupported(
                "Source code is unavailable for this step run."
            )
        return _code_lines(str(code), start_line, end_line, {})
