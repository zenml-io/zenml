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
"""The Model Control Plane: models, versions and stage changes."""

from __future__ import annotations

import re
from typing import Any, Literal

from zenml_mcp import common
from zenml_mcp.call import ZenMLCall
from zenml_mcp.client import (
    ZenMLBadRequest,
    ZenMLNotFound,
    ZenMLRestClient,
)
from zenml_mcp.common import (
    body_of,
    is_uuid,
    meta_of,
    name_of,
    read_tool,
    ref_of,
    res_of,
    segment,
    write_tool,
)
from zenml_mcp.credentials import redact
from zenml_mcp.registry import Tools

_STAGES = ("staging", "production", "archived")


def _model_of(mv: dict[str, Any], asked: str) -> dict[str, Any]:
    """The version's model as {id, name}; the name or ID the caller gave fills gaps.

    Args:
        mv: The model version, as ZenML answered it.
        asked: The model name or ID the caller gave.

    Returns:
        The model's `id` and `name`.
    """
    model = body_of(mv).get("model")
    model = model if isinstance(model, dict) else {}
    return {
        "id": model.get("id") or (asked.strip() if is_uuid(asked) else None),
        "name": model.get("name") or asked.strip(),
    }


async def _find_model_version(
    client: ZenMLRestClient,
    model: str,
    version: str | None,
    project: str | None,
) -> dict[str, Any]:
    """A hydrated model version by model (name or ID) and version.

    `version` is a number ("4" or "v4"), a version name, or a stage: latest
    (the default: the newest version), staging, production or archived.

    Args:
        client: The caller's ZenML client.
        model: A model name or ID.
        version: A version number, name or stage; None means latest.
        project: A project name or ID; None means the caller's default.

    Returns:
        The hydrated model version.

    Raises:
        ZenMLNotFound: If the model, or the version asked for, doesn't exist.
    """
    wanted = (version or "latest").strip()
    lowered = wanted.lower()
    base: dict[str, Any] = {
        "project": await common.project(client, project),
        "model": model.strip(),
        "hydrate": True,
        "sort_by": "desc:number",
        "size": 1,
    }
    attempts: list[dict[str, Any]] = []
    if lowered == "latest":
        attempts.append({})
    elif lowered in _STAGES:
        attempts.append({"stage": lowered})
    elif wanted.isdigit():
        attempts.append({"number": int(wanted)})
    else:
        attempts.append({"name": f"equals:{wanted}"})
        if re.fullmatch(r"[vV]\d+", wanted):
            attempts.append({"number": int(wanted[1:])})
    for extra in attempts:
        page = await client.get(
            "/model_versions",
            params={**base, **extra},
            what="Finding the model version",
        )
        items = page.get("items") or []
        if items:
            return items[0]
    no_model = (
        f"No model named {model!r} in this project. "
        "Check the name or id, for example with a list tool."
    )
    try:
        await common.by_name_or_id(
            client,
            "/models",
            model.strip(),
            noun="model",
            missing=no_model,
            project=base["project"],
        )
    except ZenMLNotFound:
        raise ZenMLNotFound(no_model) from None
    if lowered == "latest":
        raise ZenMLNotFound(f"Model {model!r} has no versions yet.")
    if lowered in _STAGES:
        raise ZenMLNotFound(f"No version of model {model!r} is in {lowered}.")
    raise ZenMLNotFound(f"Model {model!r} has no version {wanted!r}.")


async def _dashboard_url(
    client: ZenMLRestClient, mv: dict[str, Any]
) -> str | None:
    """ZenML Pro's page for a model version; the OSS dashboard has none.

    Args:
        client: The caller's ZenML client.
        mv: The model version.

    Returns:
        The page's URL on ZenML Pro, or None on open source.
    """
    info = await common.server_info(client)
    if not info.is_pro:
        return None
    project_id = body_of(mv).get("project_id")
    return f"{info.dashboard_url}/projects/{project_id}/model-versions/{mv.get('id')}"


def register(tools: Tools) -> None:
    """Register the Model Control Plane tools.

    Args:
        tools: The registry the tools are added to.
    """

    @read_tool(tools, "List models")
    async def zenml_list_models(
        call: ZenMLCall,
        project: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """List models in the Model Control Plane with their latest version."""  # noqa: DOC101, DOC103, DOC201
        return await common.list_page(
            call.client,
            "/models",
            page=page,
            size=size,
            what="Listing models",
            item=lambda m: {
                "id": m.get("id"),
                "name": m.get("name"),
                "latest_version": res_of(m).get("latest_version_name"),
                "latest_version_id": res_of(m).get("latest_version_id"),
                "tags": [t.get("name") for t in res_of(m).get("tags") or []],
            },
            project=project,
            sort_by="desc:latest_version",
        )

    @read_tool(tools, "Get a model version")
    async def zenml_get_model_version(
        call: ZenMLCall,
        model: str,
        version: str | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        """Get a model version: stage (staging, production…), logged metrics and the runs and artifacts linked to it.

        `model` is a model name or ID; `version` is a version number or name,
        or a stage such as latest, staging, production or archived, defaulting
        to the latest version.
        """  # noqa: DOC101, DOC103, DOC201
        client = call.client
        mv = await _find_model_version(client, model, version, project)
        artifacts, runs = await common.gather(
            client.get(
                "/model_version_artifacts",
                params={"model_version_id": mv["id"], "size": 50},
                what="Listing linked artifacts",
            ),
            client.get(
                "/model_version_pipeline_runs",
                params={
                    "model_version_id": mv["id"],
                    "size": 10,
                    "sort_by": "desc:created",
                },
                what="Listing linked runs",
            ),
        )
        return {
            "id": mv.get("id"),
            "model": name_of(body_of(mv).get("model")),
            "version": mv.get("name"),
            "number": body_of(mv).get("number"),
            "stage": body_of(mv).get("stage"),
            "description": meta_of(mv).get("description"),
            "metrics": redact(meta_of(mv).get("run_metadata")),
            "artifacts": [
                {
                    "artifact_version_id": (
                        body_of(link).get("artifact_version") or {}
                    ).get("id"),
                    "artifact": name_of(
                        body_of(body_of(link).get("artifact_version")).get(
                            "artifact"
                        )
                    ),
                    "type": body_of(body_of(link).get("artifact_version")).get(
                        "type"
                    ),
                }
                for link in artifacts.get("items", [])
            ],
            "runs": [
                ref_of(body_of(link).get("pipeline_run"))
                for link in runs.get("items", [])
            ],
        }

    @write_tool(tools, "Change a model version's stage", destructive=True)
    async def zenml_set_model_version_stage(
        call: ZenMLCall,
        model: str,
        version: str,
        stage: Literal["staging", "production", "archived"],
        force: bool = False,
        project: str | None = None,
    ) -> dict[str, Any]:
        """Move a model version to the staging, production or archived stage.

        Only do this when the user asked for it. A model has at most one
        version in staging and one in production: if another version holds
        the target stage, the call fails and names it; `force=true` replaces
        it, and ZenML archives the version that held the stage. Pass force
        only once the user agreed to replace that version (typically the one
        in production). `model` is a model name or ID; `version` is a version
        number or name, or a stage such as latest or staging.
        """  # noqa: DOC101, DOC103, DOC201, DOC501, DOC503
        client = call.client
        mv = await _find_model_version(client, model, version, project)
        body = body_of(mv)
        model_ref = _model_of(mv, model)
        current = body.get("stage")
        outcome: dict[str, Any] = {
            "outcome": "unchanged",
            "id": mv.get("id"),
            "model": model_ref["name"],
            "version": mv.get("name"),
            "stage": stage,
            "previous_stage": current,
            "archived": None,
            "dashboard_url": await _dashboard_url(client, mv),
        }
        if current == stage:
            return outcome
        holder = None
        if stage != "archived":
            page = await client.get(
                "/model_versions",
                params={
                    "project": body.get("project_id"),
                    "model": model_ref["id"] or model_ref["name"],
                    "stage": stage,
                    "size": 1,
                },
                what=f"Finding the version in {stage}",
            )
            others = [
                v for v in page.get("items") or [] if v.get("id") != mv["id"]
            ]
            holder = others[0] if others else None
            if holder and not force:
                raise ZenMLBadRequest(
                    f"{model_ref['name']} version {holder.get('name')} is in {stage}. "
                    f"Moving version {mv.get('name')} there archives version "
                    f"{holder.get('name')}; call again with force=true once the "
                    "user has agreed to replace it."
                )
        # ZenML looks for a holder in every stage, archived too, where many
        # versions sit: archiving a version never needs the user's force.
        updated = await client.write(
            "PUT",
            f"/model_versions/{segment(mv['id'])}",
            json={
                "stage": stage,
                "force": holder is not None or stage == "archived",
            },
            what=f"Moving {model_ref['name']} version {mv.get('name')} to {stage}",
        )
        new_stage = (
            body_of(updated).get("stage")
            if isinstance(updated, dict)
            else None
        ) or stage
        outcome.update(
            {
                "outcome": "stage_changed",
                "stage": new_stage,
                "archived": {
                    "id": holder.get("id"),
                    "version": holder.get("name"),
                }
                if holder
                else None,
            }
        )
        return outcome
