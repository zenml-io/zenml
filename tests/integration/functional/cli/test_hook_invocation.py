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
"""Test `zenml hook-invocation` CLI commands."""

from tests.cli_runner_utils import cli_runner
from zenml.cli.cli import cli
from zenml.client import Client
from zenml.enums import ExecutionStatus, HookType
from zenml.models import HookInvocationRequest
from zenml.utils.time_utils import utc_now


def _create_hook_invocation(client: Client) -> str:
    """Create one hook invocation and return its ID as a string.

    Args:
        client: The client to use for creation.

    Returns:
        The ID of the created hook invocation.
    """
    run = client.list_pipeline_runs().items[0]
    request = HookInvocationRequest(
        project=client.active_project.id,
        hook_type=HookType.CUSTOM,
        name="test_hook_invocation_cli",
        status=ExecutionStatus.COMPLETED,
        start_time=utc_now(),
        end_time=utc_now(),
        pipeline_run_id=run.id,
    )
    invocation = client.zen_store.create_hook_invocation(request)
    return str(invocation.id)


def test_hook_invocation_list(clean_client_with_run: Client) -> None:
    """Test that `zenml hook-invocation list` does not fail."""
    _create_hook_invocation(clean_client_with_run)
    runner = cli_runner()
    list_command = cli.commands["hook-invocation"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_hook_invocation_describe(clean_client_with_run: Client) -> None:
    """Test that `zenml hook-invocation describe` does not fail."""
    hook_invocation_id = _create_hook_invocation(clean_client_with_run)
    runner = cli_runner()
    describe_command = cli.commands["hook-invocation"].commands["describe"]
    result = runner.invoke(describe_command, [hook_invocation_id])
    assert result.exit_code == 0


def test_hook_invocation_delete(clean_client_with_run: Client) -> None:
    """Test that `zenml hook-invocation delete` does not fail."""
    hook_invocation_id = _create_hook_invocation(clean_client_with_run)
    runner = cli_runner()
    delete_command = cli.commands["hook-invocation"].commands["delete"]
    result = runner.invoke(delete_command, [hook_invocation_id])
    assert result.exit_code == 0
    assert clean_client_with_run.list_hook_invocations().total == 0
