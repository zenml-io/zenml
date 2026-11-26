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
"""Account, projects, pipelines, pipeline runs and the artifact versions they output.

`zenml_get_active_user` and `zenml_get_active_project` are mcp-zenml's
`get_active_user` and `get_active_project` (`3de0643`). The caller's default
project stands in for the SDK's active project.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timezone
from typing import Any

from zenml_mcp import common
from zenml_mcp.call import ZenMLCall
from zenml_mcp.client import (
    ZenMLBadRequest,
    ZenMLNotFound,
    ZenMLPermissionDenied,
    ZenMLRestClient,
    ZenMLRestError,
)
from zenml_mcp.common import (
    body_of,
    clip,
    default_project_id,
    iso,
    meta_of,
    name_of,
    read_tool,
    ref_of,
    res_of,
    seconds_between,
    segment,
)
from zenml_mcp.credentials import redact
from zenml_mcp.registry import Tools
from zenml_mcp.resources import projected
from zenml_mcp.runs import (
    DONE_STATUSES,
    FINAL_RUN_STATUSES,
    exception_info,
    metadata_scalars,
    resolve_run,
    run_steps,
    run_summary,
    run_with_url,
    step_health,
    takeaway,
)

logger = logging.getLogger(__name__)

RUNS_DEFAULT = 30
RUNS_MAX = 50
# Step health reads one run graph per run, so it covers fewer runs than the history.
HEALTH_RUNS = 10
SNAPSHOTS_MAX = 10
METRICS_MAX = 8
VISUALIZATION_MAX_CHARS = 20_000


def _zenml_time(value: str) -> str:
    """Accept a date or ISO timestamp and return ZenML's `%Y-%m-%d %H:%M:%S` (UTC).

    Args:
        value: A date or ISO-8601 timestamp.

    Returns:
        The time in UTC, as ZenML's filters take it.

    Raises:
        ZenMLBadRequest: If `value` is not a date or time.
    """
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ZenMLBadRequest(
            f"{value!r} is not a date or time; use e.g. 2026-10-05 or 2026-10-05 14:30:00"
        ) from error
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _model_version_ref(model_version: Any) -> dict[str, Any] | None:
    """The model version a run produced or used: {id, model, version, number, stage}.

    Args:
        model_version: The run's `model_version` resource.

    Returns:
        The model version, or None when absent or hidden by RBAC.
    """
    if not isinstance(model_version, dict) or model_version.get(
        "permission_denied"
    ):
        return None
    body = body_of(model_version)
    return {
        "id": model_version.get("id"),
        "model": name_of(body.get("model")),
        "version": model_version.get("name"),
        "number": body.get("number"),
        "stage": body.get("stage"),
    }


async def _previous_completed_run(
    client: ZenMLRestClient, run: dict[str, Any]
) -> dict[str, Any] | None:
    """The completed run of the same pipeline just before `run`, if any.

    It is what "compare with the previous run" means: the last run that
    completed, skipping failed ones in between.

    Args:
        client: The caller's client.
        run: The run read by ID.

    Returns:
        The previous completed run with its metadata, or None.
    """
    body, pipeline = body_of(run), ref_of(res_of(run).get("pipeline"))
    index = body.get("index")
    if not pipeline or not pipeline.get("id") or not isinstance(index, int):
        return None
    page = await client.get(
        "/runs",
        params={
            "project": body.get("project_id"),
            "pipeline_id": pipeline["id"],
            "status": "completed",
            "index": f"lt:{index}",
            "sort_by": "desc:index",
            "hydrate": True,
            "size": 1,
        },
        what="Finding the previous run",
    )
    items = page.get("items") or []
    if not items:
        return None
    previous = items[0]
    return {
        "id": previous.get("id"),
        "name": previous.get("name"),
        "index": body_of(previous).get("index"),
        "status": body_of(previous).get("status"),
        "created": iso(body_of(previous).get("created")),
        "metadata": metadata_scalars(meta_of(previous).get("run_metadata")),
    }


async def _failed_step_exception(
    client: ZenMLRestClient, run: dict[str, Any]
) -> dict[str, Any] | None:
    """The exception of the first failed step that recorded one.

    Orchestrators that run steps in-process record the error on the failed
    step, not on the run.

    Args:
        client: The caller's client.
        run: The run whose steps failed.

    Returns:
        The exception with its step's name, or None when no step recorded one.
    """
    failed_steps = await client.get(
        "/steps",
        params={
            "project": body_of(run).get("project_id"),
            "pipeline_run_id": run["id"],
            "status": "failed",
            "exclude_retried": True,
            "hydrate": True,
            "size": 5,
        },
        what="Reading the failed steps",
    )
    for failed_step in failed_steps.get("items") or []:
        exception = exception_info(meta_of(failed_step).get("exception_info"))
        if exception:
            exception["step"] = failed_step.get("name")
            return exception
    return None


async def _load_pipeline_run(
    client: ZenMLRestClient, run: str, project: str | None
) -> dict[str, Any]:
    """One run with its steps (graph order inputs), failure and dashboard link.

    Args:
        client: The caller's client.
        run: The run's ID or name.
        project: The project to find a named run in.

    Returns:
        The run as `zenml_get_pipeline_run` answers it.
    """
    data = await resolve_run(client, run, project)
    dag = await client.get(
        f"/runs/{segment(data['id'])}/dag", what="Reading the run graph"
    )
    steps = run_steps(dag)
    failed = [s for s in steps if s["status"] == "failed"]
    meta, res = meta_of(data), res_of(data)
    exception = exception_info(meta.get("exception_info"))
    if exception is None and failed:
        exception = await _failed_step_exception(client, data)
    code_ref = res.get("code_reference")
    previous = None
    if body_of(data).get("status") in FINAL_RUN_STATUSES:
        try:
            previous = await _previous_completed_run(client, data)
        except ZenMLRestError as error:  # a side lookup never fails the run
            logger.info("Could not find the previous run: %s", error.kind)
    result = await run_with_url(client, data)
    result.update(
        {
            "index": body_of(data).get("index"),
            "steps": steps,
            "failed_steps": [s["name"] for s in failed],
            "exception": exception,
            "snapshot": ref_of(res.get("snapshot")),
            "original_run": ref_of(res.get("original_run")),
            "waiting_for_input": ref_of(res.get("active_wait_condition")),
            "code_reference": {
                "commit": body_of(code_ref).get("commit"),
                "subdirectory": body_of(code_ref).get("subdirectory"),
                "code_repository": ref_of(
                    body_of(code_ref).get("code_repository")
                ),
            }
            if isinstance(code_ref, dict)
            else None,
            "parameters": redact((meta.get("config") or {}).get("parameters")),
            "metadata": metadata_scalars(meta.get("run_metadata")),
            "model_version": _model_version_ref(res.get("model_version")),
            "previous_run": previous,
        }
    )
    return result


def _metrics(run_metadata: Any) -> dict[str, float]:
    """A run's numeric metadata (e.g. accuracy), never values under credential-like keys.

    Args:
        run_metadata: The run's metadata.

    Returns:
        Up to `METRICS_MAX` numeric values by key.
    """
    if not isinstance(run_metadata, dict):
        return {}
    metrics: dict[str, float] = {}
    for key, value in redact(run_metadata).items():
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        metrics[str(key)] = value
        if len(metrics) >= METRICS_MAX:
            break
    return metrics


def _named(entity: Any) -> str | None:
    ref = ref_of(entity)
    return ref.get("name") if ref else None


def _model_version(entity: Any) -> dict[str, Any] | None:
    if not isinstance(entity, dict) or entity.get("permission_denied"):
        return None
    return {
        "id": entity.get("id"),
        "model": _named(body_of(entity).get("model")),
        "version": entity.get("name"),
    }


def _history_run(run: dict[str, Any]) -> dict[str, Any]:
    body, meta, res = body_of(run), meta_of(run), res_of(run)
    start, end = iso(meta.get("start_time")), iso(meta.get("end_time"))
    return {
        "id": run.get("id"),
        "name": run.get("name"),
        "index": body.get("index"),
        "status": body.get("status"),
        "created": iso(body.get("created")),
        "start_time": start,
        "end_time": end,
        "duration_seconds": seconds_between(start, end),
        "user": _named(res.get("user")),
        "stack": _named(res.get("stack")),
        "model_version": _model_version(res.get("model_version")),
        "metrics": _metrics(meta.get("run_metadata")),
    }


def _snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    body, res = body_of(snapshot), res_of(snapshot)
    schedule = res.get("schedule")
    schedule_info = None
    if isinstance(schedule, dict) and not schedule.get("permission_denied"):
        schedule_body = body_of(schedule)
        schedule_info = {
            "name": schedule.get("name"),
            "cron_expression": schedule_body.get("cron_expression"),
            "active": schedule_body.get("active"),
        }
    return {
        "id": snapshot.get("id"),
        "name": snapshot.get("name"),
        "runnable": body.get("runnable"),
        "stack": ref_of(res.get("stack")),
        "created": iso(body.get("created")),
        "latest_run_status": res.get("latest_run_status"),
        "schedule": schedule_info,
    }


async def _run_graph(
    client: ZenMLRestClient, run_id: Any
) -> dict[str, Any] | None:
    try:
        return await client.get(
            f"/runs/{segment(run_id)}/dag", what="Reading a run graph"
        )
    except ZenMLRestError:
        # One unreadable run leaves the other runs' step health intact.
        return None


def register(tools: Tools) -> None:
    """Register the account, project, pipeline and pipeline run tools.

    Args:
        tools: Where the tools are registered.
    """

    @read_tool(tools, "Show ZenML connection")
    async def zenml_get_current_user(call: ZenMLCall) -> dict[str, Any]:
        """Show which ZenML server, workspace and user this connection acts as.

        Use this first when you need to know where pipelines will be tracked,
        which project is the default, or to check the connection works.
        """  # noqa: DOC101, DOC103, DOC201
        client = call.client
        info = await common.server_info(client)
        user = await client.get(
            "/current-user", what="Reading the current user"
        )
        body = body_of(user)
        return {
            "server": {
                "url": info.url,
                "version": info.version,
                "is_zenml_pro": info.is_pro,
                "organization": info.organization,
                "workspace": info.workspace,
                "dashboard_url": info.dashboard_url,
            },
            "user": {
                "id": user.get("id"),
                "name": user.get("name"),
                "full_name": body.get("full_name"),
                "is_service_account": body.get("is_service_account"),
            },
            "default_project": await common.project(client, None),
        }

    @read_tool(tools, "List ZenML projects")
    async def zenml_list_projects(
        call: ZenMLCall, page: int = 1, size: int = 20
    ) -> dict[str, Any]:
        """List the projects in this ZenML workspace (pipelines and runs live in a project)."""  # noqa: DOC101, DOC103, DOC201
        common.check_page(page, size)
        data = await call.client.get(
            "/projects",
            params={"page": page, "size": size, "sort_by": "asc:name"},
            what="Listing projects",
        )
        answer = common.page_of(
            data,
            [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "display_name": body_of(p).get("display_name"),
                }
                for p in data.get("items") or []
            ],
        )
        return common.fit_page(answer, page=page, size=size)

    @read_tool(tools, "List pipelines")
    async def zenml_list_pipelines(
        call: ZenMLCall,
        project: str | None = None,
        name_contains: str | None = None,
        latest_run_status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """List pipelines with the status of their latest run, most recently run first.

        Use `latest_run_status="failed"` to find pipelines whose last run failed.
        """  # noqa: DOC101, DOC103, DOC201
        return await common.list_page(
            call.client,
            "/pipelines",
            page=page,
            size=size,
            what="Listing pipelines",
            item=lambda p: {
                "id": p.get("id"),
                "name": p.get("name"),
                "latest_run_id": res_of(p).get("latest_run_id"),
                "latest_run_status": res_of(p).get("latest_run_status"),
                "tags": [t.get("name") for t in res_of(p).get("tags") or []],
            },
            project=project,
            name=f"contains:{name_contains}" if name_contains else None,
            latest_run_status=latest_run_status,
            sort_by="desc:latest_run",
        )

    @read_tool(tools, "Get a pipeline")
    async def zenml_get_pipeline(
        call: ZenMLCall,
        pipeline: str,
        project: str | None = None,
        last_runs: int = RUNS_DEFAULT,
    ) -> dict[str, Any]:
        """Get a pipeline's health: its recent runs, how each step fared, a one-line takeaway and its snapshots.

        `pipeline` is a pipeline name or ID. The result lists the last
        `last_runs` runs (default 30, max 50; newest first) with status,
        duration, stack and model version; per step, its failures, cache hits
        and average duration over the last 10 runs; a one-sentence `takeaway`
        computed from those runs (e.g. "2 of the last 4 runs failed, both in
        train_model"); the named snapshots zenml_run_snapshot can start; and a
        dashboard link.
        """  # noqa: DOC101, DOC103, DOC201
        client = call.client
        data = await common.by_name_or_id(
            client,
            "/pipelines",
            pipeline,
            noun="pipeline",
            missing=f"No pipeline named {pipeline!r} in this project.",
            hydrate=True,
            project=project,
        )
        pipeline_id = data["id"]
        project_id = body_of(data).get("project_id")
        runs_page, snapshots_page, info, project_label = await common.gather(
            client.get(
                "/runs",
                params={
                    "project": project_id,
                    "pipeline_id": pipeline_id,
                    "sort_by": "desc:created",
                    "size": max(1, min(last_runs, RUNS_MAX)),
                    # Start and end times (durations) and run metadata are hydrated fields.
                    "hydrate": True,
                },
                what="Listing the pipeline's runs",
            ),
            client.get(
                "/pipeline_snapshots",
                params={
                    "project": project_id,
                    "pipeline": pipeline_id,
                    "named_only": True,
                    "sort_by": "desc:created",
                    "size": SNAPSHOTS_MAX,
                },
                what="Listing the pipeline's snapshots",
            ),
            common.server_info(client),
            common.project_name(client, project_id),
        )
        runs = [_history_run(r) for r in runs_page.get("items") or []]
        window = runs[:HEALTH_RUNS]
        dags = await common.gather(
            *(_run_graph(client, r["id"]) for r in window)
        )
        steps, failed_in, graphs_read = step_health(window, list(dags))
        durations = [
            r["duration_seconds"]
            for r in window
            if r["status"] in DONE_STATUSES
            and r["duration_seconds"] is not None
        ]
        # The dashboard addresses projects by ID on ZenML Pro and by name on OSS.
        url_project = project_id if info.is_pro else project_label
        latest = runs[0] if runs else None
        return {
            "id": pipeline_id,
            "name": data.get("name"),
            "description": meta_of(data).get("description"),
            "tags": [t.get("name") for t in res_of(data).get("tags") or []],
            "project": project_label,
            "workspace": info.workspace,
            "dashboard_url": f"{info.dashboard_url}/projects/{url_project}"
            f"/pipelines/{segment(pipeline_id)}/runs",
            "run_count": runs_page.get("total"),
            "latest_run": {
                k: latest[k]
                for k in ("id", "name", "index", "status", "created")
            }
            if latest
            else None,
            "takeaway": takeaway(str(data.get("name")), window, failed_in),
            "health": {
                "runs": len(window),
                "failed": sum(1 for r in window if r["status"] == "failed"),
                "completed": sum(
                    1 for r in window if r["status"] in DONE_STATUSES
                ),
                "median_duration_seconds": round(
                    statistics.median(durations), 1
                )
                if durations
                else None,
            },
            "step_names": [s["name"] for s in steps],
            "steps": steps,
            "step_health_runs": graphs_read,
            "runs": runs,
            "snapshots": [
                _snapshot(s) for s in snapshots_page.get("items") or []
            ],
        }

    @read_tool(tools, "List pipeline runs")
    async def zenml_list_pipeline_runs(
        call: ZenMLCall,
        project: str | None = None,
        pipeline: str | None = None,
        status: str | None = None,
        stack: str | None = None,
        created_after: str | None = None,
        in_progress: bool | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """List pipeline runs, newest first.

        Filters: `pipeline` and `stack` take a name or ID; `status` is a ZenML run
        status such as failed, running, completed, paused; `created_after` is a UTC
        time like "2026-10-05 00:00:00". Use this to find the latest failed run.
        """  # noqa: DOC101, DOC103, DOC201
        return await common.list_page(
            call.client,
            "/runs",
            page=page,
            size=size,
            what="Listing pipeline runs",
            item=run_summary,
            project=project,
            pipeline=pipeline,
            status=status,
            stack=stack,
            created=f"gte:{_zenml_time(created_after)}"
            if created_after
            else None,
            in_progress=in_progress,
            sort_by="desc:created",
        )

    @read_tool(tools, "Get a pipeline run")
    async def zenml_get_pipeline_run(
        call: ZenMLCall, run: str, project: str | None = None
    ) -> dict[str, Any]:
        """Get one pipeline run with its steps, their order and status, and any error.

        `run` is a run ID or run name. The result lists every step with its
        status, duration, upstream steps and output artifacts, the first failed
        step, and the run's exception (message, failing user code line,
        traceback tail). Use the step IDs with zenml_get_step_run,
        zenml_get_step_logs and zenml_get_step_code.
        """  # noqa: DOC101, DOC103, DOC201
        return await _load_pipeline_run(call.client, run, project)


def register_artifacts(tools: Tools) -> None:
    """Register the artifact version tools.

    Args:
        tools: Where the tools are registered.
    """

    @read_tool(tools, "List artifact versions")
    async def zenml_list_artifact_versions(
        call: ZenMLCall,
        project: str | None = None,
        run: str | None = None,
        artifact: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """List artifact versions (step outputs), optionally for one run (`run` ID or name) or one artifact name."""  # noqa: DOC101, DOC103, DOC201
        return await common.list_page(
            call.client,
            "/artifact_versions",
            page=page,
            size=size,
            what="Listing artifact versions",
            item=lambda a: {
                "id": a.get("id"),
                "artifact": name_of(body_of(a).get("artifact")),
                "version": body_of(a).get("version"),
                "type": body_of(a).get("type"),
                "producer_step_run_id": res_of(a).get("producer_step_run_id"),
                "created": iso(body_of(a).get("created")),
            },
            project=project,
            pipeline_run=run,
            artifact=artifact,
            sort_by="desc:created",
        )

    @read_tool(tools, "Get an artifact version")
    async def zenml_get_artifact_version(
        call: ZenMLCall,
        artifact_version_id: str,
        include_visualization: bool = False,
    ) -> dict[str, Any]:
        """Get an artifact version's type, metadata and producing step; optionally its first text visualization.

        Never downloads the artifact data itself. Image visualizations are only
        listed, not returned.
        """  # noqa: DOC101, DOC103, DOC201
        client = call.client
        data = await client.get(
            f"/artifact_versions/{segment(artifact_version_id)}",
            what="Reading the artifact version",
        )
        body, meta, res = body_of(data), meta_of(data), res_of(data)
        data_type = body.get("data_type")
        visualizations = [
            body_of(v).get("type")
            for v in meta.get("visualizations") or []
            if isinstance(v, dict)
        ]
        result: dict[str, Any] = {
            "id": data.get("id"),
            "artifact": name_of(body.get("artifact")),
            "version": body.get("version"),
            "type": body.get("type"),
            "data_type": data_type.get("attribute")
            if isinstance(data_type, dict)
            else data_type,
            "producer_step_run_id": res.get("producer_step_run_id"),
            "producer_pipeline_run_id": res.get("producer_pipeline_run_id"),
            "metadata": redact(meta.get("run_metadata")),
            "visualization_types": visualizations,
        }
        if include_visualization and visualizations:
            index = next(
                (
                    i
                    for i, kind in enumerate(visualizations)
                    if kind != "image"
                ),
                None,
            )
            if index is not None:
                try:
                    loaded = await client.get(
                        f"/artifact_versions/{segment(data['id'])}/visualize",
                        params={"index": index},
                        what="Loading the visualization",
                    )
                except (ZenMLPermissionDenied, ZenMLNotFound) as error:
                    result["visualization_unavailable"] = error.message
                else:
                    value, clipped = clip(
                        str(loaded.get("value", "")), VISUALIZATION_MAX_CHARS
                    )
                    result["visualization"] = {
                        "type": loaded.get("type"),
                        "value": value,
                        "truncated": clipped,
                    }
        result["uri"] = body.get("uri")
        return result


# mcp-zenml's description of `get_active_project`, verbatim.
_GET_ACTIVE_PROJECT = """Get the currently active project.

    Projects are organizational containers for ZenML resources. Most SDK methods
    are project-scoped, and this tool returns the default project context.
    """


def register_active(tools: Tools) -> None:
    """Register mcp-zenml's active user and active project tools.

    Args:
        tools: Where the tools are registered.
    """

    @read_tool(tools, None)
    async def zenml_get_active_user(call: ZenMLCall) -> dict[str, Any]:
        """Get the currently active user."""  # noqa: DOC101, DOC103, DOC201
        client = call.client
        user = await client.get(
            "/current-user",
            params={"hydrate": True},
            what="Reading the current user",
        )
        return projected(user, resource_type="user")

    @read_tool(tools, None, description=_GET_ACTIVE_PROJECT)
    async def zenml_get_active_project(call: ZenMLCall) -> dict[str, Any]:
        client = call.client
        project_id = await default_project_id(client)
        project = await client.get(
            f"/projects/{segment(project_id)}",
            params={"hydrate": True},
            what="Reading the active project",
        )
        return redact(project)
