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
"""Snapshots and run control: start, replay, stop and answer paused runs."""

from __future__ import annotations

from typing import Any, Literal

from zenml_mcp import common
from zenml_mcp.call import Sensitive, ZenMLCall
from zenml_mcp.client import ZenMLRestError
from zenml_mcp.common import (
    body_of,
    iso,
    meta_of,
    page_of,
    read_tool,
    ref_of,
    res_of,
    segment,
    write_tool,
)
from zenml_mcp.credentials import redact, refuse_run_credentials
from zenml_mcp.registry import Tools
from zenml_mcp.runs import resolve_run, started_run

_TEMPLATE_KEYS = ("run_name", "enable_cache", "parameters", "tags")


def _run_config_template(template: Any) -> dict[str, Any] | None:
    """The overridable parts of a snapshot's run configuration.

    Settings, environment variables, secrets and `extra` are left out: they can
    carry credentials, and zenml_run_snapshot doesn't accept Docker settings anyway.

    Args:
        template: The snapshot's `config_template`.

    Returns:
        The run name, cache setting, parameters, tags and step parameters,
        with credentials masked, or None when the template is not a dict.
    """
    if not isinstance(template, dict):
        return None
    result = {k: template[k] for k in _TEMPLATE_KEYS if k in template}
    steps = template.get("steps") or {}
    step_parameters = {
        name: config.get("parameters")
        for name, config in steps.items()
        if isinstance(config, dict) and config.get("parameters")
    }
    if step_parameters:
        result["step_parameters"] = step_parameters
    return redact(result)


def register_snapshots(tools: Tools) -> None:
    """Register the tools that list, read and run snapshots.

    Args:
        tools: Where the tools are registered.
    """

    @read_tool(tools, "List snapshots")
    async def zenml_list_snapshots(
        call: ZenMLCall,
        project: str | None = None,
        pipeline: str | None = None,
        runnable_only: bool = True,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """List named pipeline snapshots: frozen, runnable versions of a pipeline that zenml_run_snapshot can start."""  # noqa: DOC101, DOC103, DOC201
        return await common.list_page(
            call.client,
            "/pipeline_snapshots",
            page=page,
            size=size,
            what="Listing snapshots",
            item=lambda s: {
                "id": s.get("id"),
                "name": s.get("name"),
                "pipeline": ref_of(res_of(s).get("pipeline")),
                "stack": ref_of(res_of(s).get("stack")),
                "runnable": body_of(s).get("runnable"),
                "latest_run_status": res_of(s).get("latest_run_status"),
                "created": iso(body_of(s).get("created")),
            },
            project=project,
            pipeline=pipeline,
            named_only=True,
            runnable=True if runnable_only else None,
            sort_by="desc:created",
        )

    @read_tool(tools, "Get a snapshot")
    async def zenml_get_snapshot(
        call: ZenMLCall, snapshot_id: str
    ) -> dict[str, Any]:
        """Get a snapshot and the run configuration it accepts (use it before zenml_run_snapshot)."""  # noqa: DOC101, DOC103, DOC201
        client = call.client
        data = await client.get(
            f"/pipeline_snapshots/{segment(snapshot_id)}",
            params={
                "include_config_schema": True,
                "step_configuration_filter": "__none__",
            },
            what="Reading the snapshot",
        )
        meta = meta_of(data)
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "pipeline": ref_of(res_of(data).get("pipeline")),
            "stack": ref_of(res_of(data).get("stack")),
            "runnable": body_of(data).get("runnable"),
            "is_dynamic": body_of(data).get("is_dynamic"),
            "description": meta.get("description"),
            "run_configuration_template": _run_config_template(
                meta.get("config_template")
            ),
        }

    @write_tool(
        tools,
        "Run a snapshot",
        destructive=True,
        open_world=True,
        sensitive=Sensitive("Starting a pipeline run"),
    )
    async def zenml_run_snapshot(
        call: ZenMLCall,
        snapshot_id: str,
        run_name: str | None = None,
        step_parameters: dict[str, dict[str, Any]] | None = None,
        enable_cache: bool | None = None,
    ) -> dict[str, Any]:
        """Start a new pipeline run from a runnable snapshot on its remote stack.

        Use this when the code cannot be run from a shell (for example in a chat
        without a terminal). `step_parameters` maps step name to parameter
        overrides. This starts compute on the snapshot's stack. Returns the
        queued run; follow it with zenml_get_pipeline_run.
        """  # noqa: DOC101, DOC103, DOC201
        run_configuration: dict[str, Any] = {}
        if run_name:
            run_configuration["run_name"] = run_name
        if enable_cache is not None:
            run_configuration["enable_cache"] = enable_cache
        if step_parameters:
            run_configuration["steps"] = {
                step: {"parameters": params}
                for step, params in step_parameters.items()
            }
        refuse_run_credentials(
            step_parameters, "step_parameters", "read it in the step instead"
        )
        client = call.client
        run = await client.write(
            "POST",
            f"/pipeline_snapshots/{segment(snapshot_id)}/runs",
            json={"run_configuration": run_configuration, "step_run": None},
            what="Starting a run from the snapshot",
        )
        return {
            "outcome": "started",
            "run": await started_run(client, run),
        }


def register_run_control(tools: Tools) -> None:
    """Register the tools that replay, stop and answer pipeline runs.

    Args:
        tools: Where the tools are registered.
    """

    @write_tool(
        tools,
        "Rerun a pipeline run",
        destructive=True,
        open_world=True,
        sensitive=Sensitive("Replaying a pipeline run"),
    )
    async def zenml_replay_pipeline_run(
        call: ZenMLCall,
        run: str,
        skip_successful_steps: bool = False,
        enable_cache: bool | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        """Start a new run that replays an earlier run's snapshot and configuration on its stack.

        Set `skip_successful_steps` to reuse the outputs of steps that already
        succeeded and only rerun the rest. Needs a ZenML server that can run
        pipelines itself; otherwise rerun the code from a shell.
        """  # noqa: DOC101, DOC103, DOC201
        client = call.client
        original = await resolve_run(client, run, project)
        config: dict[str, Any] = {
            "skip_successful_steps": skip_successful_steps
        }
        if enable_cache is not None:
            config["enable_cache"] = enable_cache
        new_run = await client.write(
            "POST",
            f"/runs/{segment(original['id'])}/replay",
            json=config,
            what="Replaying the run",
        )
        return {
            "outcome": "started",
            "replayed_run_id": original["id"],
            "run": await started_run(client, new_run),
        }

    @write_tool(
        tools,
        "Stop a pipeline run",
        destructive=True,
        sensitive=Sensitive("Stopping a pipeline run"),
    )
    async def zenml_stop_pipeline_run(
        call: ZenMLCall, run: str, project: str | None = None
    ) -> dict[str, Any]:
        """Ask the orchestrator to stop a running pipeline run gracefully (running steps finish, no new steps start)."""  # noqa: DOC101, DOC103, DOC201
        client = call.client
        target = await resolve_run(client, run, project)
        await client.write(
            "POST",
            f"/runs/{segment(target['id'])}/stop",
            params={"graceful": True},
            what="Stopping the run",
        )
        try:
            status = await client.get(
                f"/runs/{segment(target['id'])}/status",
                what="Reading the run status",
            )
        except ZenMLRestError:
            status = (
                None  # the stop was accepted; don't invite a second request
            )
        return {
            "outcome": "stop_requested",
            "run_id": target["id"],
            "status": status,
        }

    @read_tool(tools, "List runs waiting for input")
    async def zenml_list_pending_run_inputs(
        call: ZenMLCall,
        project: str | None = None,
        run: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """List paused runs that are waiting for a human answer, with the question and the expected answer format."""  # noqa: DOC101, DOC103, DOC201
        common.check_page(page, size)
        client = call.client
        data = await client.get(
            "/run_wait_conditions",
            params={
                "project": await common.project(client, project),
                "status": "pending",
                "pipeline_run": run,
                "hydrate": True,
                "sort_by": "desc:created",
                "page": page,
                "size": size,
            },
            what="Listing runs waiting for input",
        )
        answer = page_of(
            data,
            [
                {
                    "id": w.get("id"),
                    "name": w.get("name"),
                    "run": ref_of(res_of(w).get("run")),
                    "question": meta_of(w).get("question"),
                    "answer_schema": meta_of(w).get("data_schema"),
                    "created": iso(body_of(w).get("created")),
                }
                for w in data.get("items", [])
            ],
        )
        return common.fit_page(answer, page=page, size=size)

    @write_tool(
        tools,
        "Answer a paused run",
        destructive=True,
        sensitive=Sensitive("Resuming or stopping a paused run"),
    )
    async def zenml_resolve_run_input(
        call: ZenMLCall,
        wait_condition_id: str,
        action: Literal["continue", "abort"],
        answer: Any = None,
    ) -> dict[str, Any]:
        """Answer a paused run: `continue` resumes it with an `answer` matching its schema; `abort` stops it.

        This is how a paused run is resumed. Only answer with what the user
        decided; never invent an approval.
        """  # noqa: DOC101, DOC103, DOC201
        client = call.client
        payload: dict[str, Any] = {"resolution": action}
        if answer is not None:
            payload["result"] = answer
        data = await client.write(
            "PUT",
            f"/run_wait_conditions/{segment(wait_condition_id)}/resolve",
            json=payload,
            what="Answering the paused run",
        )
        return {
            "outcome": "resolved",
            "id": data.get("id")
            if isinstance(data, dict)
            else wait_condition_id,
            "resolution": action,
            "status": body_of(data).get("status")
            if isinstance(data, dict)
            else None,
        }
