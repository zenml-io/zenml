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
"""`zenml_trigger_pipeline`: mcp-zenml's `trigger_pipeline` (`3de0643`).

Upstream calls the ZenML SDK's `Client.trigger_pipeline`. This one sends the
REST requests that method sends: it finds the snapshot to run, refuses what the SDK
refuses before starting, and starts the run as the calling user.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any, cast

from mcp.types import CallToolResult

from zenml_mcp import common
from zenml_mcp.call import Sensitive, ZenMLCall
from zenml_mcp.client import (
    UNREADABLE,
    ZenMLBadRequest,
    ZenMLNotFound,
    ZenMLOutcomeUnknown,
    ZenMLRestClient,
    ZenMLUnavailable,
)
from zenml_mcp.common import (
    answer_lost,
    body_of,
    canonical_uuid,
    default_project_id,
    meta_of,
    res_of,
    segment,
    unknown_outcome,
    write_tool,
)
from zenml_mcp.credentials import refuse_run_credentials
from zenml_mcp.registry import Tools
from zenml_mcp.resources import (
    SDK_PAGE_SIZE,
    find,
    parses_as,
    projected,
)

# The search for a runnable snapshot reads at most this many pages of
# `SDK_PAGE_SIZE` snapshots and checks at most this many builds; the SDK reads
# every page.
SNAPSHOT_SEARCH_PAGES = 5
SNAPSHOT_SEARCH_BUILDS = 20

_NOTHING_TO_START = "Provide at least one of pipeline_name_or_id, snapshot_name_or_id, or template_id."
_TEMPLATE_DEPRECATION = (
    "The `template_id` parameter is deprecated. "
    "Please use `snapshot_name_or_id` instead. The supported ZenML "
    "version retains run-template CRUD APIs, while snapshots are "
    "preferred for new workflows."
)

# The SDK turns a run configuration into its own models before sending it, so
# each step and each of these objects named in it also carries its model's
# defaults, and ZenML applies the ones that are not null: a named step that
# sets no heartbeat threshold gets 30, a `retry` given only `max_retries` gets
# a delay of 0. Sent here too, so a run is configured as one started through
# mcp-zenml is. These are ZenML 0.97.0's defaults; `test_contract.py` checks
# them against the models in zenml core.
_SDK_STEP_DEFAULTS = {"heartbeat_healthy_threshold": 30, "outputs": {}}
_SDK_OBJECT_DEFAULTS: dict[str, dict[str, Any]] = {
    "retry": {"max_retries": 1, "delay": 0, "backoff": 0},
    "cache_policy": {
        "include_step_code": True,
        "include_step_parameters": True,
        "include_artifact_values": True,
        "include_artifact_ids": True,
    },
    "model": {"save_models_to_registry": True},
    "group": {"type": "manual"},
}


async def _snapshot(
    client: ZenMLRestClient, snapshot: str, pipeline: str | None, project: str
) -> dict[str, Any]:
    """The snapshot the SDK's `trigger_pipeline` would run.

    An id, or an exact name in the caller's default project, narrowed by
    `pipeline`. No prefixes.

    Args:
        client: The caller's ZenML client.
        snapshot: The snapshot's id or exact name.
        pipeline: A pipeline name or ID that narrows a name, or None.
        project: The ID of the project a name is looked up in.

    Returns:
        The snapshot, not hydrated.

    Raises:
        ZenMLNotFound: If no snapshot, or more than one, has that name.
    """
    known = canonical_uuid(snapshot)
    if known:
        return await client.get(
            f"/pipeline_snapshots/{segment(known)}",
            params={"hydrate": False},
            what="Reading the snapshot",
        )
    page = await client.page(
        "/pipeline_snapshots",
        params={
            "name": snapshot,
            "pipeline": pipeline,
            "project": project,
            "hydrate": False,
            "size": 1,
        },
        what="Finding the snapshot",
    )
    if page["total"] == 1:
        return page["items"][0]
    if page["total"] == 0:
        raise ZenMLNotFound(f"No snapshot named {snapshot!r} was found.")
    raise ZenMLNotFound(
        f"{page['total']} snapshots are named {snapshot!r}. Pass "
        "pipeline_name_or_id, or the snapshot's id."
    )


async def _hydrated(
    client: ZenMLRestClient, route: str, entity: dict[str, Any]
) -> dict[str, Any]:
    """The entity with its metadata, read again hydrated when ZenML left it out.

    This is how the SDK's models read a missing part.

    Args:
        client: The caller's ZenML client.
        route: The entity's list route, such as `/stacks`.
        entity: The entity, as ZenML answered it.

    Returns:
        The entity with its metadata.
    """
    if entity.get("metadata") is not None:
        return entity
    return await client.get(
        f"{route}/{segment(entity['id'])}",
        params={"hydrate": True},
        what="Reading what a snapshot runs on",
    )


_CUSTOM_FLAVOR = (
    "Unable to run pipeline from the server on a stack that includes stack "
    "components with a custom flavor."
)


_LOCAL_COMPONENT = (
    "Unable to run pipeline from the server on a stack that includes local "
    "stack components."
)


_LOCAL_REGISTRY = re.compile(r"localhost:[0-9]{4,5}")
_LOCAL_KUBERNETES_CONTEXTS = (
    "k3d-",
    "kind-",
    "minikube",
    "docker-desktop",
    "colima",
    "rancher-desktop",
)


# The text pydantic reads as false. ZenML keeps a stored configuration as
# sent, and its config class parses the text when it reads the component.
_FALSE_TEXT = frozenset({"0", "f", "false", "n", "no", "off"})


def _flag(value: Any) -> bool:
    """A stored boolean as ZenML's config reads it: `"false"` is false.

    Args:
        value: The stored value.

    Returns:
        The boolean ZenML reads; text it can't read counts as true, which
        takes the component as local and refuses it.
    """
    if isinstance(value, str):
        return value.strip().lower() not in _FALSE_TEXT
    return bool(value)


def _always(configuration: Mapping[str, Any]) -> bool:
    return True


def _set_to(field: str, default: bool) -> Callable[[Mapping[str, Any]], bool]:
    return lambda configuration: _flag(configuration.get(field, default))


def _local_kubernetes_deployer(configuration: Mapping[str, Any]) -> bool:
    context = str(configuration.get("kubernetes_context") or "").lower()
    return _flag(configuration.get("local", False)) or any(
        marker in context for marker in _LOCAL_KUBERNETES_CONTEXTS
    )


def _local_feature_store(configuration: Mapping[str, Any]) -> bool:
    host = configuration.get("online_host", "localhost")
    return host in ("localhost", "127.0.0.1")


def _local_data_context(configuration: Mapping[str, Any]) -> bool:
    return configuration.get("context_root_dir") is not None


def _local_mlflow_tracking(configuration: Mapping[str, Any]) -> bool:
    uri = str(configuration.get("tracking_uri") or "")
    return not (uri.startswith(("http://", "https://")) or uri == "databricks")


_FLAVORS = "zenml.integrations"
# ZenML 0.97.0's own flavors whose components can be local (`is_local`), by
# the flavor's source, with how a component's configuration decides it, its
# fields' defaults included. Container registries are decided by type below.
# `test_contract.py` checks the table against the flavors in zenml core.
_LOCAL_WHEN: Mapping[str, Callable[[Mapping[str, Any]], bool]] = {
    "zenml.orchestrators.local.local_orchestrator.LocalOrchestratorFlavor": _always,
    "zenml.orchestrators.local_docker.local_docker_orchestrator."
    "LocalDockerOrchestratorFlavor": _always,
    "zenml.artifact_stores.local_artifact_store.LocalArtifactStoreFlavor": _always,
    "zenml.deployers.local.local_deployer.LocalDeployerFlavor": _always,
    "zenml.deployers.docker.docker_deployer.DockerDeployerFlavor": _always,
    "zenml.sandboxes.docker_sandbox.DockerSandboxFlavor": _always,
    "zenml.sandboxes.local_sandbox.LocalSandboxFlavor": _always,
    f"{_FLAVORS}.airflow.flavors.airflow_orchestrator_flavor."
    "AirflowOrchestratorFlavor": _set_to("local", True),
    f"{_FLAVORS}.kubernetes.flavors.kubernetes_orchestrator_flavor."
    "KubernetesOrchestratorFlavor": _set_to("local", False),
    f"{_FLAVORS}.kubernetes.flavors.kubernetes_deployer_flavor."
    "KubernetesDeployerFlavor": _local_kubernetes_deployer,
    f"{_FLAVORS}.feast.flavors.feast_feature_store_flavor."
    "FeastFeatureStoreFlavor": _local_feature_store,
    f"{_FLAVORS}.great_expectations.flavors."
    "great_expectations_data_validator_flavor."
    "GreatExpectationsDataValidatorFlavor": _local_data_context,
    f"{_FLAVORS}.mlflow.flavors.mlflow_model_deployer_flavor."
    "MLFlowModelDeployerFlavor": _always,
    f"{_FLAVORS}.mlflow.flavors.mlflow_experiment_tracker_flavor."
    "MLFlowExperimentTrackerFlavor": _local_mlflow_tracking,
}


def _is_local(
    flavor: Mapping[str, Any], configuration: Mapping[str, Any]
) -> bool:
    """A component's `is_local`, as the SDK decides it.

    The SDK reads it from the flavor's class installed next to it. This
    server knows ZenML's own flavors and takes any other flavor as not local.

    Args:
        flavor: The component's flavor.
        configuration: The component's configuration.

    Returns:
        Whether the component is local.
    """
    body = body_of(flavor)
    if body.get("type") == "container_registry":
        uri = str(configuration.get("uri") or "").rstrip("/")
        return bool(_LOCAL_REGISTRY.fullmatch(uri))
    local_when = _LOCAL_WHEN.get(body.get("source") or "")
    return local_when is not None and local_when(configuration)


async def _refuse_unrunnable_stack(
    client: ZenMLRestClient, stack: dict[str, Any]
) -> None:
    """The SDK's `validate_stack_is_runnable_from_server`.

    A component of a custom flavor, or a local one, is refused as a
    `ValueError`.

    Args:
        client: The caller's ZenML client.
        stack: The stack to check.

    Raises:
        ZenMLBadRequest: If a component has a custom flavor or is local, or
            where the SDK's assertions fail: a type with several components,
            or a flavor not found exactly once.
    """
    stack = await _hydrated(client, "/stacks", stack)
    for components in (meta_of(stack).get("components") or {}).values():
        # The SDK asserts one component per type and one flavor per component;
        # where its assertion would fail, the stack is refused as invalid.
        if len(components) != 1:
            raise ZenMLBadRequest(
                "Unable to run pipeline from the server on a stack with "
                "several components of one type."
            )
        for component in components:
            flavors = await client.get(
                "/flavors",
                params={
                    "name": body_of(component).get("flavor_name"),
                    "type": body_of(component).get("type"),
                    "hydrate": False,
                    "size": SDK_PAGE_SIZE,
                },
                what="Reading a component's flavor",
            )
            found = flavors.get("items") or []
            if len(found) != 1:
                raise ZenMLBadRequest(
                    "Unable to run pipeline from the server on a stack with "
                    "a component whose flavor is not found exactly once."
                )
            if body_of(found[0]).get("is_custom"):
                raise ZenMLBadRequest(_CUSTOM_FLAVOR)
            # The SDK reads the configuration, which hydrates the component.
            hydrated = await _hydrated(client, "/components", component)
            if _is_local(
                found[0], meta_of(hydrated).get("configuration") or {}
            ):
                raise ZenMLBadRequest(_LOCAL_COMPONENT)


async def _newest_runnable_snapshot(
    client: ZenMLRestClient, pipeline: str, stack: str | None, project: str
) -> dict[str, Any]:
    """The newest named, runnable snapshot of a pipeline, as the SDK chooses it.

    It runs on `stack` if given, and its build's stack has no component of a
    custom flavor and no local one. A named stack with one is refused.

    Args:
        client: The caller's ZenML client.
        pipeline: The pipeline's name or ID.
        stack: A stack name or ID to run on, or None.
        project: The ID of the project the pipeline is looked up in.

    Returns:
        The snapshot.

    Raises:
        ZenMLBadRequest: If ZenML refuses a build's stack with a status other
            than 400 or 422.
        ZenMLNotFound: If no runnable snapshot is found in the search.
    """
    found = await find(client, "pipeline", pipeline, project_id=project)
    on_stack = (
        await find(client, "stack", stack, name_prefix=False)
        if stack
        else None
    )
    if on_stack is not None:
        await _refuse_unrunnable_stack(client, on_stack)
    params = {
        "pipeline": found["id"],
        "stack": on_stack["id"] if on_stack else None,
        "project": body_of(found).get("project_id"),
        "runnable": True,
        "named_only": True,
        "sort_by": "desc:created",
        "hydrate": False,
        "size": SDK_PAGE_SIZE,
    }
    page = await client.page(
        "/pipeline_snapshots",
        params=params,
        what="Finding a runnable snapshot",
    )
    snapshots = list(page["items"])
    while page["index"] < min(page["total_pages"], SNAPSHOT_SEARCH_PAGES):
        page = await client.page(
            "/pipeline_snapshots",
            params={**params, "page": page["index"] + 1},
            what="Finding a runnable snapshot",
        )
        snapshots += page["items"]
    checked = 0
    for snapshot in snapshots:
        build = res_of(snapshot).get("build")
        if not build:
            continue
        if checked == SNAPSHOT_SEARCH_BUILDS:
            break
        checked += 1
        on = meta_of(await _hydrated(client, "/pipeline_builds", build)).get(
            "stack"
        )
        if not on:
            continue
        try:
            await _refuse_unrunnable_stack(client, on)
        except ZenMLBadRequest as error:
            # The SDK skips a snapshot whose check it refuses itself, or that
            # ZenML refuses with a 400 or 422.
            if error.status not in (None, 400, 422):
                raise
            continue
        return snapshot
    searched = (
        f" among its newest {len(snapshots)} snapshots ({checked} builds checked)"
        if page["index"] < page["total_pages"]
        or checked == SNAPSHOT_SEARCH_BUILDS
        else ""
    )
    raise ZenMLNotFound(
        f"Pipeline {pipeline!r} has no runnable snapshot"
        + (f" on stack {stack!r}" if stack else "")
        + f"{searched}. Pass snapshot_name_or_id or template_id to choose one.",
    )


def _refuse_unrunnable_configuration(
    configuration: dict[str, Any], *, is_dynamic: bool
) -> None:
    """The SDK's `validate_run_config_is_runnable_from_server`, before the start.

    Args:
        configuration: The run configuration.
        is_dynamic: Whether the snapshot's pipeline is dynamic.

    Raises:
        ZenMLBadRequest: If it sets a static pipeline's parameters, a build, a
            schedule or Docker settings.
    """
    if configuration.get("parameters") and not is_dynamic:
        raise ZenMLBadRequest(
            "Can't set pipeline parameters when running a static pipeline via "
            "the REST API."
        )
    for key in ("build", "schedule"):
        if configuration.get(key):
            raise ZenMLBadRequest(
                f"Can't set {key} when running pipeline via Rest API."
            )
    steps = configuration.get("steps")
    settings = [
        configuration.get("settings"),
        *(
            step.get("settings")
            for step in (steps.values() if isinstance(steps, dict) else ())
            if isinstance(step, dict)
        ),
    ]
    # The SDK refuses any `docker` entry: an empty one becomes a settings object,
    # and a null one fails its validation.
    if any(isinstance(each, dict) and "docker" in each for each in settings):
        raise ZenMLBadRequest(
            "Can't set DockerSettings when running pipeline via Rest API."
        )


def _with_object_defaults(configuration: dict[str, Any]) -> dict[str, Any]:
    filled = dict(configuration)
    for key, defaults in _SDK_OBJECT_DEFAULTS.items():
        if isinstance(filled.get(key), dict):
            filled[key] = {**defaults, **filled[key]}
    model = filled.get("model")
    if isinstance(model, dict):
        # The SDK's model refuses a version id unless this flag came with it,
        # then always sets the flag. ZenML reads the flag as permission, so
        # sending it without the refusal would let any caller pin a version.
        flag = "suppress_class_validation_warnings"
        if model.get("model_version_id") and not model.get(flag):
            raise ZenMLBadRequest(
                "`model_version_id` field is for internal use only"
            )
        model[flag] = True
    return filled


def _as_the_sdk_sends(
    run_configuration: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """A run configuration with the defaults the SDK adds to it.

    Args:
        run_configuration: The caller's run configuration, or None.

    Returns:
        The configuration with the SDK's defaults, or None.
    """
    if run_configuration is None:
        return None
    filled = _with_object_defaults(run_configuration)
    if isinstance(filled.get("steps"), dict):
        filled["steps"] = {
            name: _with_object_defaults({**_SDK_STEP_DEFAULTS, **step})
            if isinstance(step, dict)
            else step
            for name, step in filled["steps"].items()
        }
    return filled


def _started(run: Any) -> Any:
    """The run ZenML answered with, as the generic get would return it.

    Args:
        run: ZenML's answer to the start.

    Returns:
        The run, projected as a pipeline run.

    Raises:
        ZenMLBadRequest: If the answer isn't a pipeline run, as the SDK fails
            to parse it.
    """
    if not parses_as("pipeline_run", run):
        # As the SDK fails to parse it: upstream reports invalid input, though
        # the run may have started.
        raise ZenMLBadRequest(UNREADABLE)
    return projected(run, resource_type="pipeline_run")


def _unknown_start(pipeline: str | None, project_id: str) -> CallToolResult:
    """mcp-zenml's answer to a start whose response, or a read before it, was lost.

    Args:
        pipeline: The pipeline name or ID the caller gave, or None.
        project_id: The caller's default project's ID.

    Returns:
        An unknown-outcome tool result that says not to retry.
    """
    reconciliation = {
        "operation": None,
        "resource_type": "pipeline_run",
        "pipeline_name_or_id": pipeline,
        "project_id": project_id,
        "new_run_id": None,
        "reconcilable": False,
        "note": (
            "The source pipeline cannot prove whether a new run was created because "
            "the new run ID is unavailable; do not retry automatically."
        ),
    }
    unknown = {
        "resource_type": "pipeline_run",
        "operation": "trigger",
        "outcome": "unknown",
        "pipeline_name_or_id": pipeline,
        "project_id": project_id,
        "new_run_id": None,
        "reconciliation": reconciliation,
    }
    message = (
        "The response was lost or could not be decoded after the pipeline "
        "trigger may have been dispatched, so the outcome is unknown. The new "
        "run ID is unavailable, and the source pipeline cannot prove success; "
        "do not retry automatically."
    )
    return unknown_outcome("trigger_pipeline", message, unknown)


async def _start(
    client: ZenMLRestClient,
    project_id: str,
    snapshot_name_or_id: str | None,
    pipeline_name_or_id: str | None,
    stack_name_or_id: str | None,
    template_id: str | None,
    configuration: dict[str, Any] | None,
) -> dict[str, Any]:
    if template_id:
        if configuration is not None:
            _refuse_unrunnable_configuration(configuration, is_dynamic=False)
        run = await client.write(
            "POST",
            f"/run_templates/{segment(template_id)}/runs",
            json=configuration or {},
            what="Starting a run from the run template",
        )
        return {
            "pipeline_run": _started(run),
            "deprecation_warning": _TEMPLATE_DEPRECATION,
        }
    if snapshot_name_or_id:
        snapshot = await _snapshot(
            client, snapshot_name_or_id, pipeline_name_or_id, project_id
        )
    else:
        snapshot = await _newest_runnable_snapshot(
            client,
            cast(str, pipeline_name_or_id),
            stack_name_or_id,
            project_id,
        )
    if configuration is not None:
        _refuse_unrunnable_configuration(
            configuration, is_dynamic=bool(body_of(snapshot).get("is_dynamic"))
        )
    run = await client.write(
        "POST",
        f"/pipeline_snapshots/{segment(snapshot['id'])}/runs",
        json={}
        if configuration is None
        else {"run_configuration": configuration},
        what="Starting a run from the snapshot",
    )
    return {"pipeline_run": _started(run)}


# mcp-zenml's description of `trigger_pipeline`, verbatim.
_TRIGGER_PIPELINE = """Trigger a pipeline to run from the server.

    Args:
        pipeline_name_or_id: Optional name or ID of the pipeline to trigger. A
            snapshot or template can be triggered without it.
        snapshot_name_or_id: The name or ID of a specific snapshot to run (preferred)
        stack_name_or_id: Optional stack override for the run
        template_id: Deprecated template-based trigger parameter. Use
            `snapshot_name_or_id` for new integrations. The supported ZenML
            version still retains run-template CRUD APIs.

        run_configuration: Optional ZenML run configuration overrides, including
            step parameters, substitutions, and cache settings. Validated by the
            ZenML SDK before triggering the run.

    Usage examples:
        * Run the latest runnable snapshot for a pipeline:
        ```python
        trigger_pipeline(pipeline_name_or_id=<NAME>)
        ```
        * Run the latest runnable snapshot for a pipeline on a specific stack:
        ```python
        trigger_pipeline(
            pipeline_name_or_id=<NAME>,
            stack_name_or_id=<STACK_NAME_OR_ID>
        )
        ```
        * Run a specific snapshot (RECOMMENDED):
        ```python
        trigger_pipeline(
            snapshot_name_or_id=<SNAPSHOT_NAME_OR_ID>
        )
        ```
        * Run a specific template (DEPRECATED - use snapshot_name_or_id instead):
        ```python
        trigger_pipeline(template_id=<ID>)
        ```
    """


def register(tools: Tools) -> None:
    """Register the pipeline trigger tool.

    Args:
        tools: The registry the tool is added to.
    """

    # A run executes the pipeline's own code, which can change or delete data
    # and reach other systems; the standalone server declares the same hints.
    @write_tool(
        tools,
        None,
        destructive=True,
        open_world=True,
        description=_TRIGGER_PIPELINE,
        sensitive=Sensitive("Starting a pipeline run"),
    )
    async def zenml_trigger_pipeline(
        call: ZenMLCall,
        snapshot_name_or_id: str | None = None,
        pipeline_name_or_id: str | None = None,
        stack_name_or_id: str | None = None,
        template_id: str | None = None,
        run_configuration: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if snapshot_name_or_id is not None and template_id is not None:
            raise ZenMLBadRequest(
                "snapshot_name_or_id and template_id are mutually exclusive; "
                "provide only one."
            )
        # Like the SDK, an empty name is no name: a lookup of "" would match
        # by prefix whatever single pipeline the project holds.
        if not (pipeline_name_or_id or snapshot_name_or_id or template_id):
            raise ZenMLBadRequest(_NOTHING_TO_START)
        refuse_run_credentials(run_configuration)
        configuration = _as_the_sdk_sends(run_configuration)
        client = call.client
        # Resolved once: a project name that moves to another project during
        # the start can't split the lookups from the reconciliation.
        project_id = await default_project_id(client)
        try:
            return await _start(
                client,
                project_id,
                snapshot_name_or_id,
                pipeline_name_or_id,
                stack_name_or_id,
                template_id,
                configuration,
            )
        except (ZenMLOutcomeUnknown, ZenMLUnavailable) as error:
            if not answer_lost(error):
                raise
            # A lost answer is a `CallToolResult`, which the SDK passes through.
            return cast(
                dict[str, Any], _unknown_start(pipeline_name_or_id, project_id)
            )
