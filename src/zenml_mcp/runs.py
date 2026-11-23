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
"""Pipeline runs: their shapes, how one is found, and the health of a run graph."""

from __future__ import annotations

import math
import statistics
from collections import Counter
from typing import Any

from zenml_mcp.client import ZenMLRestClient
from zenml_mcp.common import (
    body_of,
    by_name_or_id,
    is_uuid,
    iso,
    meta_of,
    project_name,
    ref_of,
    res_of,
    seconds_between,
    segment,
    server_info,
)
from zenml_mcp.credentials import redact

TRACEBACK_MAX_LINES = 40
METADATA_MAX_KEYS = 40
METADATA_MAX_CHARS = 300
FINAL_RUN_STATUSES = frozenset(
    {"completed", "failed", "cached", "stopped", "cancelled"}
)
DONE_STATUSES = frozenset({"completed", "cached"})


def metadata_scalars(raw: Any) -> dict[str, Any]:
    """Logged run or step metadata as {key: value}.

    JSON scalars only (long strings are clipped), credential-like keys masked,
    at most `METADATA_MAX_KEYS` keys. Dicts, lists and non-finite numbers are
    left out. ZenML keeps the latest value per key, so a key logged once per
    epoch shows its newest value.

    Args:
        raw: The logged metadata, as the server returns it.

    Returns:
        The scalar values by key.
    """
    if not isinstance(raw, dict):
        return {}
    result: dict[str, Any] = {}
    for key, value in raw.items():
        if len(result) >= METADATA_MAX_KEYS:
            break
        if isinstance(value, float) and not math.isfinite(value):
            continue
        if isinstance(value, str) and len(value) > METADATA_MAX_CHARS:
            value = value[:METADATA_MAX_CHARS] + "…"
        if isinstance(value, bool | int | float | str):
            result[str(key)] = value
    return redact(result)


def exception_info(info: Any) -> dict[str, Any] | None:
    """An exception's info, its traceback cut to the last lines.

    Args:
        info: An `exception_info` field, as the server returns it.

    Returns:
        The message, the failing user code line, the source and the last
        `TRACEBACK_MAX_LINES` traceback lines, or None when there is neither
        a message nor a traceback.
    """
    if not isinstance(info, dict) or not (
        info.get("message") or info.get("traceback")
    ):
        return None
    lines = (info.get("traceback") or "").splitlines()
    return {
        "message": info.get("message"),
        "user_code_line": info.get("user_code_line"),
        "source": info.get("source"),
        "traceback": "\n".join(lines[-TRACEBACK_MAX_LINES:]),
        "traceback_truncated": len(lines) > TRACEBACK_MAX_LINES,
    }


def run_summary(run: dict[str, Any], url: str | None = None) -> dict[str, Any]:
    """A pipeline run's summary.

    Args:
        run: The run, as the server returns it.
        url: The run's dashboard link, if known.

    Returns:
        The run's ID, name, status, pipeline, stack and times, with its
        duration once it has a start or end time.
    """
    body, meta, res = body_of(run), meta_of(run), res_of(run)
    start = iso(meta.get("start_time"))
    end = iso(meta.get("end_time"))
    summary: dict[str, Any] = {
        "id": run.get("id"),
        "name": run.get("name"),
        "status": body.get("status"),
        "status_reason": body.get("status_reason"),
        "pipeline": ref_of(res.get("pipeline")),
        "stack": ref_of(res.get("stack")),
        "created": iso(body.get("created")),
        "updated": iso(body.get("updated")),
    }
    if start or end:
        summary["start_time"] = start
        summary["end_time"] = end
        summary["duration_seconds"] = seconds_between(start, end)
    if url:
        summary["dashboard_url"] = url
    return summary


async def run_url(client: ZenMLRestClient, run: dict[str, Any]) -> str:
    """Dashboard link to a run: Pro uses the project ID, OSS the project name.

    Args:
        client: The client of the server the run is on.
        run: The run.

    Returns:
        The link.
    """
    info = await server_info(client)
    project_id = body_of(run).get("project_id")
    if info.is_pro:
        return (
            f"{info.dashboard_url}/projects/{project_id}/runs/{run.get('id')}"
        )
    name = await project_name(client, project_id)
    return f"{info.dashboard_url}/projects/{name}/runs/{run.get('id')}"


async def run_with_url(
    client: ZenMLRestClient, run: dict[str, Any]
) -> dict[str, Any]:
    """A run's summary with its dashboard link.

    Args:
        client: The client of the server the run is on.
        run: The run.

    Returns:
        The run's summary, with `dashboard_url`.
    """
    return run_summary(run, await run_url(client, run))


async def resolve_run(
    client: ZenMLRestClient, run: str, project: str | None
) -> dict[str, Any]:
    """A run found by its name or ID.

    A run found by name comes from the list route, so it is read again by
    its ID.

    Args:
        client: The client to read with.
        run: The run's name or ID.
        project: The project to look in for a name, if not the default.

    Returns:
        The run, as the server returns it.
    """
    found = await by_name_or_id(
        client,
        "/runs",
        run,
        noun="run",
        missing=f"No pipeline run named {run!r} in this project.",
        project=project,
    )
    if is_uuid(run):
        return found
    return await client.get(
        f"/runs/{segment(found['id'])}", what="Reading the run"
    )


def _graph(
    dag: dict[str, Any],
) -> tuple[dict[str, Any], list[Any], dict[str, set[str]], dict[str, str]]:
    """A run graph's nodes, steps, upstream steps and artifact producers.

    A step is upstream of another through a direct edge or through an
    artifact it produced.

    Args:
        dag: The run graph, as the server returns it.

    Returns:
        The graph's nodes by ID, its step nodes, each step's upstream steps
        and each artifact's producing step.
    """
    nodes = dag.get("nodes") or []
    edges = dag.get("edges") or []
    by_node = {n.get("node_id"): n for n in nodes}
    steps = [n for n in nodes if n.get("type") == "step"]
    upstream: dict[str, set[str]] = {n.get("node_id"): set() for n in steps}
    producer: dict[str, str] = {}
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        if by_node.get(source, {}).get("type") == "step" and target in by_node:
            if by_node[target].get("type") == "step":
                upstream.setdefault(target, set()).add(source)
            else:
                producer[target] = source
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        if target in upstream and source in producer:
            upstream[target].add(producer[source])
    return by_node, steps, upstream, producer


def run_steps(dag: dict[str, Any]) -> list[dict[str, Any]]:
    """A run graph's steps with their upstream steps and output artifacts.

    Args:
        dag: The run graph, as the server returns it.

    Returns:
        Each step's name, ID, status, timing, upstream steps and output
        artifacts.
    """
    by_node, step_nodes, upstream, producer = _graph(dag)
    outputs: dict[str, list[str]] = {}
    for artifact_node, step_node in producer.items():
        artifact_name = by_node[artifact_node].get("name")
        if artifact_name:
            outputs.setdefault(step_node, []).append(artifact_name)
    steps = []
    for node in step_nodes:
        meta = node.get("metadata") or {}
        steps.append(
            {
                "name": node.get("name"),
                "step_run_id": node.get("id"),
                "status": meta.get("status"),
                "start_time": iso(meta.get("start_time")),
                "duration_seconds": meta.get("duration"),
                "upstream_steps": sorted(
                    by_node[u].get("name")
                    for u in upstream.get(node.get("node_id"), ())
                ),
                "output_artifacts": sorted(
                    outputs.get(node.get("node_id"), [])
                ),
            }
        )
    return steps


def _step_graph(dag: dict[str, Any]) -> list[dict[str, Any]]:
    """A run graph's step nodes in pipeline order: by depth, then as the server listed them.

    Args:
        dag: The run graph, as the server returns it.

    Returns:
        The step nodes, in that order.
    """
    _, steps, upstream, _ = _graph(dag)
    depth: dict[str, int] = {}

    def depth_of(node_id: str, seen: frozenset[str] = frozenset()) -> int:
        if node_id in depth:
            return depth[node_id]
        if node_id in seen:
            return 0
        value = max(
            (
                depth_of(u, seen | {node_id}) + 1
                for u in upstream.get(node_id, ())
            ),
            default=0,
        )
        depth[node_id] = value
        return value

    order = {str(n.get("node_id")): i for i, n in enumerate(steps)}
    return sorted(
        steps,
        key=lambda n: (
            depth_of(str(n.get("node_id"))),
            order[str(n.get("node_id"))],
        ),
    )


def step_health(
    window: list[dict[str, Any]], dags: list[dict[str, Any] | None]
) -> tuple[list[dict[str, Any]], dict[str, list[str]], int]:
    """Per step: in how many runs it ran, failed or was cached, and its usual duration.

    Args:
        window: The runs, newest first.
        dags: Each run's graph, or None where it wasn't read.

    Returns:
        The steps in pipeline order (the newest graph's order, then steps
        only older runs had), the failed steps of each run, and how many run
        graphs were read.
    """
    order: list[str] = []
    stats: dict[str, dict[str, Any]] = {}
    failed_in: dict[str, list[str]] = {}
    read = 0
    for run, dag in zip(window, dags, strict=True):
        if dag is None:
            continue
        read += 1
        for node in _step_graph(dag):
            name = node.get("name")
            if not name:
                continue
            if name not in stats:
                order.append(name)
                stats[name] = {
                    "runs": 0,
                    "failures": 0,
                    "cached": 0,
                    "durations": [],
                    "last_status": None,
                }
            meta = node.get("metadata") or {}
            status = meta.get("status")
            if not status:
                continue
            entry = stats[name]
            entry["runs"] += 1
            entry["last_status"] = entry["last_status"] or status
            if status == "failed":
                entry["failures"] += 1
                failed_in.setdefault(str(run.get("id")), []).append(name)
            elif status == "cached":
                entry["cached"] += 1
            duration = meta.get("duration")
            if status == "completed" and isinstance(duration, int | float):
                entry["durations"].append(duration)
    steps = [
        {
            "name": name,
            "runs": stats[name]["runs"],
            "failures": stats[name]["failures"],
            "cached": stats[name]["cached"],
            "avg_duration_seconds": round(
                statistics.fmean(stats[name]["durations"]), 1
            )
            if stats[name]["durations"]
            else None,
            "last_status": stats[name]["last_status"],
        }
        for name in order
    ]
    return steps, failed_in, read


_LAST_RUN = {
    "completed": "The last run completed.",
    "cached": "The last run was cached.",
    "stopped": "The last run was stopped.",
    "cancelled": "The last run was cancelled.",
}


def takeaway(
    name: str, window: list[dict[str, Any]], failed_in: dict[str, list[str]]
) -> str:
    """One sentence about the recent runs, computed from them (never a guess).

    Args:
        name: The pipeline's name.
        window: The recent runs' summaries, newest first.
        failed_in: The failed steps of each run, by run ID.

    Returns:
        The sentence.
    """
    if not window:
        return f"No runs of {name} yet."
    failed = [r for r in window if r.get("status") == "failed"]
    if not failed:
        if len(window) == 1:
            status = window[0].get("status")
            if status in _LAST_RUN:
                return _LAST_RUN[status]
            if status not in FINAL_RUN_STATUSES:
                return "The last run is still going."
            return f"The last run ended as {status}."
        if all(r.get("status") in DONE_STATUSES for r in window):
            return f"All of the last {len(window)} runs completed."
        return f"None of the last {len(window)} runs failed."
    sentence = (
        "The last run failed"
        if len(window) == 1
        else f"{len(failed)} of the last {len(window)} runs failed"
    )
    where = [failed_in.get(str(r.get("id"))) or [] for r in failed]
    if all(len(w) == 1 and w == where[0] for w in where):
        lead = {1: "in", 2: "both in"}.get(len(failed), "all in")
        joint = " " if len(window) == 1 else ", "
        return f"{sentence}{joint}{lead} {where[0][0]}."
    counts = Counter(step for steps in where for step in steps)
    if not counts:
        return f"{sentence}."
    if len(failed) == 1:
        return f"{sentence}, in {' and '.join(where[0])}."
    parts = [f"{count} in {step}" for step, count in counts.most_common(3)]
    return f"{sentence}: {', '.join(parts)}."
