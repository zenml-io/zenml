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
"""Tests for hook output materialization."""

from uuid import uuid4

from zenml.client import Client
from zenml.enums import ExecutionStatus, HookType
from zenml.hooks.recording import _materialize_hook_outputs
from zenml.models import HookInvocationRequest
from zenml.utils.time_utils import utc_now


def test_materialize_hook_outputs_round_trips(clean_client_with_run: Client):
    """Test that a hook output value materializes into a linked artifact."""
    client = clean_client_with_run
    run = client.list_pipeline_runs().items[0]
    hook_id = uuid4()

    outputs = _materialize_hook_outputs(
        outputs={"result": 42},
        pipeline_run_id=run.id,
        hook_invocation_id=hook_id,
    )
    assert list(outputs.keys()) == ["result"]
    assert len(outputs["result"]) == 1

    created = client.zen_store.create_hook_invocation(
        HookInvocationRequest(
            id=hook_id,
            project=client.active_project.id,
            hook_type=HookType.CUSTOM,
            name="record",
            status=ExecutionStatus.COMPLETED,
            start_time=utc_now(),
            end_time=utc_now(),
            pipeline_run_id=run.id,
            outputs=outputs,
        )
    )

    fetched = client.get_hook_invocation(created.id)
    assert "result" in fetched.outputs
    version = fetched.outputs["result"][0]
    assert version.load() == 42
