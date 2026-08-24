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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""RBAC regression tests for snapshot replacement."""

import asyncio
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import pytest

from tests.unit.zen_server.rbac_harness import (
    AllowAllRBAC,
    DenyActionRBAC,
    RBACTestServer,
    rbac_test_server,
)
from zenml.client import Client
from zenml.constants import API, PIPELINE_SNAPSHOTS, VERSION_1
from zenml.models import PipelineRequest, PipelineSnapshotRequest
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.routers import pipeline_snapshot_endpoints

SNAPSHOTS_URL = API + VERSION_1 + PIPELINE_SNAPSHOTS


def _snapshot_request(
    server: RBACTestServer,
    stack_id: UUID,
    pipeline_id: UUID,
    name: Optional[str],
    replace: bool = False,
) -> PipelineSnapshotRequest:
    return PipelineSnapshotRequest(
        project=server.project.id,
        stack=stack_id,
        pipeline=pipeline_id,
        name=name,
        replace=replace,
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        client_version="test",
        server_version="test",
        step_configurations={},
    )


def _json(request: PipelineSnapshotRequest) -> Dict[str, Any]:
    return request.model_dump(mode="json", exclude_none=True)


async def _run_snapshot_replace_rbac_regression(client: Client) -> None:
    async with rbac_test_server(client, pipeline_snapshot_endpoints) as server:
        store = server.store
        stack_id = client.active_stack.id
        pipeline = store.create_pipeline(
            PipelineRequest(
                project=server.project.id, name=f"pipe-{uuid4().hex[:8]}"
            )
        )
        victim = store.create_snapshot(
            _snapshot_request(server, stack_id, pipeline.id, name="shared")
        )
        own = store.create_snapshot(
            _snapshot_request(server, stack_id, pipeline.id, name=None)
        )
        takeover = _json(
            _snapshot_request(
                server, stack_id, pipeline.id, "shared", replace=True
            )
        )

        server.use_rbac(DenyActionRBAC(Action.DELETE))
        denied_create = server.http.post(SNAPSHOTS_URL, json=takeover)
        assert denied_create.status_code == 403, denied_create.text
        denied_update = server.http.put(
            f"{SNAPSHOTS_URL}/{own.id}",
            json={"name": "shared", "replace": True},
        )
        assert denied_update.status_code == 403, denied_update.text
        assert store.get_snapshot(victim.id).name == "shared"

        # Re-asserting a snapshot's own name displaces nothing.
        self_rename = server.http.put(
            f"{SNAPSHOTS_URL}/{victim.id}",
            json={"name": "shared", "replace": True},
        )
        assert self_rename.status_code == 200, self_rename.text

        server.use_rbac(AllowAllRBAC())
        allowed_create = server.http.post(SNAPSHOTS_URL, json=takeover)
        assert allowed_create.status_code == 200, allowed_create.text
        with pytest.raises(KeyError):
            store.get_snapshot(victim.id)


def test_snapshot_replace_requires_delete_permission(
    clean_client: Client,
) -> None:
    """Replacing a named snapshot needs DELETE on the displaced snapshot."""
    asyncio.run(_run_snapshot_replace_rbac_regression(clean_client))
