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
"""Client/store round-trip tests for hook invocations."""

from zenml.client import Client
from zenml.enums import ExecutionStatus, HookType
from zenml.models import HookInvocationRequest
from zenml.utils.time_utils import utc_now


def test_hook_invocation_client_round_trip(clean_client_with_run: Client):
    """Test creating, listing, getting, and deleting a hook invocation."""
    client = clean_client_with_run
    run = client.list_pipeline_runs().items[0]

    start = utc_now()
    request = HookInvocationRequest(
        project=client.active_project.id,
        hook_type=HookType.CUSTOM,
        name="pre_tool_call",
        status=ExecutionStatus.COMPLETED,
        start_time=start,
        end_time=utc_now(),
        pipeline_run_id=run.id,
    )
    created = client.zen_store.create_hook_invocation(request)
    assert created.hook_type == HookType.CUSTOM
    assert created.pipeline_run_id == run.id

    listed = client.list_hook_invocations(pipeline_run_id=run.id)
    assert created.id in [hook.id for hook in listed.items]

    fetched = client.get_hook_invocation(created.id)
    assert fetched.id == created.id
    assert fetched.name == "pre_tool_call"

    client.delete_hook_invocation(created.id)
    assert client.list_hook_invocations(pipeline_run_id=run.id).total == 0
