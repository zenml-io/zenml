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
"""One lifecycle or relation action on a resource, behind the generic action tool.

Ported from mcp-zenml's `action_resource` (commit 3de0643). That server checks
a request, then calls the ZenML SDK. This one makes the same checks, then
sends the REST requests the SDK's method would send (ZenML 0.97.0,
`client.py` and `rest_zen_store.py`).

A key that looks like a credential is refused before any request, except a
new webhook secret when the secret page runs the action. The three deployment
actions are not offered (`not_offered` in `resource_catalog.py`), and webhook
secret rotation answers with a secret page link.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mcp.types import CallToolResult

from zenml_mcp.call import ZenMLCall, ask_if_sensitive
from zenml_mcp.client import (
    UNREADABLE,
    ZenMLBadRequest,
    ZenMLOutcomeUnknown,
    ZenMLUnavailable,
)
from zenml_mcp.common import (
    answer_lost,
    segment,
)
from zenml_mcp.credentials import (
    NEW_WEBHOOK_SECRET,
    awaiting_user,
    refuse_credentials_but_secrets,
    through_the_page,
)
from zenml_mcp.resource_catalog import get_resource_spec
from zenml_mcp.resource_spec import (
    TAGGABLE_RESOURCE,
    ResourceSpec,
    catalog_type,
    validate_action_payload,
)
from zenml_mcp.resources import (
    WriteRequest,
    exact_uuid,
    find_nested_id,
    find_nested_value,
    lost_answer,
    parses_as,
    projected,
)

_TAG_TARGETS: Mapping[str, str] = {
    target_type: catalog_type(target_type)
    for target_type in TAGGABLE_RESOURCE["enum"]
}


def _tag_parent(target_type: str) -> str | None:
    """The parent a tag target is read under; one without is listed by id.

    Args:
        target_type: The tag target's type, as the tag action names it.

    Returns:
        The parent's id field, or None for a target read by listing.
    """
    parent = get_resource_spec(_TAG_TARGETS[target_type]).parent
    return parent[0] if parent else None


def _check_tag_parents(action: str, payload: Mapping[str, Any]) -> None:
    target_type = payload["target_type"]
    expected = _tag_parent(target_type)
    supplied = {
        field
        for field in ("artifact_id", "model_id")
        if payload.get(field) is not None
    }
    if expected and expected not in supplied:
        raise ZenMLBadRequest(
            f"tag {action} for {target_type!r} requires {expected}"
        )
    unexpected = supplied - ({expected} if expected else set())
    if unexpected:
        raise ZenMLBadRequest(
            "Unexpected tag target parent identifiers: "
            + ", ".join(sorted(unexpected))
        )


async def _check_targets(request: WriteRequest, action: str) -> None:
    """What upstream reads before it acts: the resource, then what it acts on.

    Args:
        request: The checked action.
        action: The action's name.

    Raises:
        ZenMLBadRequest: When an exclusive tag would be attached without
            `allow_exclusive_replace`.
    """
    resource_type, payload = request.spec.resource_type, request.payload
    target = str(request.target)
    if resource_type == "run_wait_condition":
        await request.listed(resource_type, target)
    else:
        existing = await request.checked(
            resource_type, target, scoped=resource_type != "tag"
        )
        if (
            (resource_type, action) == ("tag", "attach")
            and find_nested_value(existing["item"], "exclusive")
            and not payload.get("allow_exclusive_replace", False)
        ):
            raise ZenMLBadRequest(
                "Attaching an exclusive tag requires allow_exclusive_replace=true"
            )
    if request.spec.trigger and payload.get("snapshot_id") is not None:
        await request.checked(
            "snapshot", exact_uuid("snapshot_id", payload["snapshot_id"])
        )
    elif resource_type == "tag":
        target_type = payload["target_type"]
        if _tag_parent(target_type):
            await request.checked(
                _TAG_TARGETS[target_type],
                payload["target_id"],
                artifact_id=payload.get("artifact_id"),
                model_id=payload.get("model_id"),
            )
        else:
            await request.listed(
                _TAG_TARGETS[target_type], payload["target_id"]
            )


async def _send(request: WriteRequest, action: str) -> Any:
    """The SDK's requests.

    Args:
        request: The checked action.
        action: The action's name.

    Returns:
        ZenML's answer to the write.
    """
    client, payload = request.client, request.payload
    resource_type, target = request.spec.resource_type, str(request.target)
    if resource_type == "pipeline_run":
        # The SDK reads the run before it asks ZenML to replay it.
        await request.read("pipeline_run", target, hydrate=False)
        configuration = dict(payload.get("run_configuration") or {})
        if "steps_to_skip" in configuration:
            # The SDK holds these in a set.
            configuration["steps_to_skip"] = list(
                dict.fromkeys(configuration["steps_to_skip"])
            )
        return await client.write(
            "POST",
            f"/runs/{segment(target)}/replay",
            json=configuration,
            what="Replaying the pipeline run",
        )
    if request.spec.trigger:
        path = f"/triggers/{segment(target)}"
        given = payload.get("snapshot_id")
        snapshot = exact_uuid("snapshot_id", given) if given else None
        if action == "clear_dispatch_error":
            return await client.write(
                "DELETE",
                f"{path}/dispatch_state",
                params={"snapshot_id": snapshot} if snapshot else None,
                what="Clearing the trigger's dispatch errors",
            )
        if action == "attach":
            return await client.write(
                "PUT",
                f"{path}/pipeline_snapshots/{segment(snapshot)}",
                json=payload.get("run_configuration"),
                params={"allow_replace": payload.get("allow_replace", False)},
                what="Attaching the trigger to the snapshot",
            )
        return await client.write(
            "DELETE",
            f"{path}/pipeline_snapshots/{segment(snapshot)}",
            what="Detaching the trigger from the snapshot",
        )
    if resource_type == "webhook":
        # The SDK reads the webhook before it rotates the secret.
        await request.read("webhook", target)
        return await client.write(
            "PUT",
            f"/webhooks/{segment(target)}/secret",
            json={"secret": payload.get("secret")},
            what="Rotating the webhook secret",
        )
    if resource_type == "run_wait_condition":
        return await client.write(
            "PUT",
            f"/run_wait_conditions/{segment(target)}/resolve",
            json={
                "resolution": payload["resolution"].lower(),
                "result": payload.get("result"),
            },
            what="Resolving the wait condition",
        )
    link = [
        {
            "tag_id": target,
            "resource_id": exact_uuid("target_id", payload["target_id"]),
            "resource_type": payload["target_type"],
        }
    ]
    method, what = (
        ("POST", "Attaching")
        if action == "attach"
        else ("DELETE", "Detaching")
    )
    return await client.write(
        method, "/tag_resources/batch", json=link, what=f"{what} the tag"
    )


def _reconciliation(
    spec: ResourceSpec,
    action: str,
    resource_id: str,
    project_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """The read that shows whether an action applied, as upstream names it.

    Args:
        spec: The resource's type.
        action: The action's name.
        resource_id: The resource it acts on.
        project_id: The resource's project.
        payload: The checked payload.

    Returns:
        The reconciliation read.
    """
    resource_type = spec.resource_type
    if resource_type == "pipeline_run":
        return {
            "operation": None,
            "resource_type": resource_type,
            "source_run_id": resource_id,
            "project_id": project_id,
            "new_run_id": None,
            "reconcilable": False,
            "note": (
                "The replay may have created a new run, but its ID was lost with "
                "the response. Reading the source run cannot confirm the replay "
                "outcome; do not replay automatically."
            ),
        }
    if spec.trigger and action in {"attach", "detach"}:
        return {
            "operation": "list",
            "resource_type": resource_type,
            "project_id": project_id,
            "filters": {
                "id": resource_id,
                "snapshot_id": payload["snapshot_id"],
            },
            "note": (
                "Confirm that the trigger attachment is present."
                if action == "attach"
                else "Confirm that the trigger attachment is absent."
            ),
        }
    if spec.trigger:
        reconciliation = {
            "operation": "get",
            "resource_type": resource_type,
            "resource_id": resource_id,
            "project_id": project_id,
            "hydrate": True,
            "note": "Inspect snapshot_dispatch_states and confirm the dispatch error fields are empty; do not repeat automatically.",
        }
        if payload.get("snapshot_id"):
            reconciliation["expected_snapshot_id"] = payload["snapshot_id"]
        return reconciliation
    if resource_type == "run_wait_condition":
        return {
            "operation": "list",
            "resource_type": resource_type,
            "project_id": project_id,
            "filters": {"id": resource_id},
            "note": "Inspect status and resolution; do not resolve again automatically.",
        }
    if resource_type == "webhook":
        return {
            "operation": "get",
            "resource_type": resource_type,
            "resource_id": resource_id,
            "project_id": project_id,
            "note": "The newly issued webhook secret cannot be recovered by a later read.",
        }
    target_type = payload["target_type"]
    reconciliation = {
        "operation": "get",
        "resource_type": _TAG_TARGETS[target_type],
        "resource_id": payload["target_id"],
        "project_id": project_id,
        "hydrate": True,
        "expected_tag_id": resource_id,
        "note": "Inspect the hydrated target tags for this exact tag ID; do not repeat automatically.",
    }
    parent = _tag_parent(target_type)
    if parent:
        reconciliation[parent] = payload[parent]
    return reconciliation


def _unreadable(resource_type: str, action: str, answer: Any) -> bool:
    """Whether ZenML's answer is not what the SDK parses it into.

    The SDK refuses a body that is not JSON, even where its method returns
    nothing.

    Args:
        resource_type: The resource's type.
        action: The action's name.
        answer: ZenML's answer.

    Returns:
        Whether the SDK would fail to parse the answer.
    """
    if resource_type in {"pipeline_run", "run_wait_condition"}:
        return not parses_as(resource_type, answer)
    if (resource_type, action) == ("tag", "attach"):
        return not (
            isinstance(answer, list)
            and all(parses_as("tag_resource", link) for link in answer)
        )
    if (resource_type, action) == ("webhook", "rotate_secret"):
        return not (
            isinstance(answer, dict) and isinstance(answer.get("secret"), str)
        )
    return isinstance(answer, str)


async def act(
    call: ZenMLCall,
    resource_type: str,
    action: str,
    resource_id: str,
    payload: dict[str, Any] | None,
    project_id: str | None,
) -> dict[str, Any] | CallToolResult:
    """Run one action, as the generic action tool does.

    Args:
        call: The tool call.
        resource_type: The catalogued type.
        action: The action's name.
        resource_id: The resource it acts on.
        payload: The action's payload.
        project_id: The resource's project.

    Returns:
        The action's outcome, a lost answer's result, or a secret page's
        answer.

    Raises:
        ZenMLBadRequest: When the arguments are refused, or ZenML's answer
            can't be read.
        ZenMLOutcomeUnknown: When a request fails and its answer was not
            lost.
        ZenMLUnavailable: When a request fails and its answer was not lost.
    """
    through = through_the_page(call)
    refuse_credentials_but_secrets(resource_type, action, payload, through)
    spec = get_resource_spec(resource_type)
    action_spec = spec.action(action)
    checked = validate_action_payload(action_spec, payload)
    ask_if_sensitive(call, action_spec.sensitive, checked)
    if resource_type == "tag":
        _check_tag_parents(action, checked)
    target = exact_uuid("resource_id", resource_id)
    if project_id is None:
        raise ZenMLBadRequest(
            f"project_id is required for {resource_type!r} actions"
        )
    project = exact_uuid("project_id", project_id)
    scope = {"kind": "project", "project_id": project, "source": "requested"}
    request = WriteRequest(
        client=call.client,
        spec=spec,
        payload=checked,
        project=project,
        target=target,
    )
    if (resource_type, action) in through:
        arguments = {
            "resource_type": resource_type,
            "action": action,
            "resource_id": resource_id,
            "payload": checked,
            "project_id": project_id,
        }
        return awaiting_user(
            call, "zenml_action_resource", arguments, (NEW_WEBHOOK_SECRET,)
        )
    await _check_targets(request, action)
    reconciliation = _reconciliation(spec, action, target, project, checked)
    try:
        answer = await _send(request, action)
    except (ZenMLOutcomeUnknown, ZenMLUnavailable) as error:
        if not answer_lost(error):
            raise
        return _unknown_action(request, action, scope, reconciliation)
    if _unreadable(resource_type, action, answer):
        # As the SDK fails to parse it: upstream reports invalid input, though
        # the action may have been applied.
        raise ZenMLBadRequest(UNREADABLE)
    result = answer if action_spec.returns else None
    response = request.outcome(
        scope,
        reconciliation,
        action=action,
        resource_id=target,
        outcome="accepted" if resource_type == "pipeline_run" else "completed",
    )
    response["sdk_method"] = action_spec.sdk_method
    if result is not None:
        response["item"] = projected(result, resource_type=resource_type)
        result_id = find_nested_id(result, "id", "id")
        status = find_nested_value(result, "status")
        if status is not None:
            response["status"] = status
        if resource_type == "pipeline_run" and result_id:
            response["new_run_id"] = result_id
            response["reconciliation"] = {
                "operation": "get",
                "resource_type": resource_type,
                "resource_id": result_id,
                "project_id": project,
                "note": "Inspect the replayed run status; do not replay automatically.",
            }
    if (resource_type, action) == ("webhook", "rotate_secret"):
        response["issued_secret"] = answer["secret"]
    if (resource_type, action) == ("tag", "attach"):
        response["exclusive_replacement_authorized"] = checked.get(
            "allow_exclusive_replace", False
        )
    return response


def _unknown_action(
    request: WriteRequest,
    action: str,
    scope: dict[str, Any],
    reconciliation: dict[str, Any],
) -> CallToolResult:
    """mcp-zenml's answer to an action whose response was lost.

    Args:
        request: The checked action.
        action: The action's name.
        scope: The effective scope.
        reconciliation: The read that shows whether the action applied.

    Returns:
        The unknown-outcome result.
    """
    unknown = request.outcome(
        scope,
        reconciliation,
        action=action,
        resource_id=request.target,
        outcome="unknown",
    )
    replay = (request.spec.resource_type, action) == ("pipeline_run", "replay")
    recovery = (
        "The created run ID is unavailable, so reading the source run "
        "cannot reconcile the outcome; do not replay automatically."
        if replay
        else "Use the supplied reconciliation read and do not repeat automatically."
    )
    return lost_answer("zenml_action_resource", "action", recovery, unknown)
