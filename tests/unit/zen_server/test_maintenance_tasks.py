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
"""Tests for maintenance task submission."""

import asyncio
from contextlib import ExitStack
from typing import Any, Callable, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zenml.zen_server import utils


def test_maintenance_task_runs_with_the_submitting_auth_context() -> None:
    """The task sees the caller's auth context, which is reset afterwards."""
    auth_context = MagicMock()
    submitted: List[Callable[[], None]] = []
    executor = MagicMock()
    executor.submit.side_effect = lambda run: submitted.append(run)
    seen: List[Optional[Any]] = []

    with (
        patch.object(utils, "maintenance_executor", return_value=executor),
        patch.object(utils, "get_auth_context", return_value=auth_context),
    ):
        task_id = utils.submit_maintenance_task(
            lambda: seen.append(utils.get_auth_context())
        )

    assert task_id and len(submitted) == 1
    submitted[0]()
    assert seen == [auth_context]
    assert utils._auth_context.get() is None


@pytest.mark.parametrize("shutdown_fails", [False, True])
def test_lifespan_manages_maintenance_before_telemetry_shutdown(
    shutdown_fails: bool,
) -> None:
    """Keep maintenance lifecycle and final telemetry cleanup together."""
    from zenml.zen_server import zen_server_api as api

    calls = MagicMock()
    executor = MagicMock()
    calls.attach_mock(executor.shutdown, "maintenance_shutdown")
    if shutdown_fails:
        executor.shutdown.side_effect = RuntimeError("maintenance shutdown")

    async def run_lifespan() -> None:
        async with api.lifespan(MagicMock()):
            calls.serving()

    with ExitStack() as stack:
        for name in (
            "initialize_zen_store",
            "initialize_resource_pool_store",
            "initialize_rbac",
            "initialize_feature_gate",
            "initialize_workload_manager",
            "initialize_snapshot_executor",
            "initialize_artifact_store_cache",
            "initialize_secure_headers",
            "cleanup_artifact_store_cache",
        ):
            stack.enter_context(patch.object(api, name))
        for name in (
            "initialize_request_manager",
            "initialize_snapshot_run_dispatcher",
            "initialize_streaming",
            "register_event_handlers",
            "register_webhook_event_handlers",
            "shutdown_snapshot_run_dispatcher",
            "shutdown_streaming",
            "cleanup_request_manager",
        ):
            stack.enter_context(
                patch.object(api, name, new_callable=AsyncMock)
            )
        stack.enter_context(patch.object(api, "service_connector_registry"))
        stack.enter_context(patch.object(api, "otel_span"))
        stack.enter_context(
            patch.object(api, "logger")
        ).isEnabledFor.return_value = False
        config = stack.enter_context(
            patch.object(api, "server_config")
        ).return_value
        config.thread_pool_size = 40
        config.is_pro_server = False
        stack.enter_context(patch.object(api, "snapshot_executor"))
        stack.enter_context(
            patch.object(api, "maintenance_executor", return_value=executor)
        )
        initialize = stack.enter_context(
            patch.object(api, "initialize_maintenance_executor")
        )
        telemetry = stack.enter_context(patch.object(api, "shutdown_otel"))
        calls.attach_mock(initialize, "maintenance_initialize")
        calls.attach_mock(telemetry, "telemetry_shutdown")
        if shutdown_fails:
            with pytest.raises(RuntimeError, match="maintenance shutdown"):
                asyncio.run(run_lifespan())
        else:
            asyncio.run(run_lifespan())

    assert [call[0] for call in calls.mock_calls] == [
        "maintenance_initialize",
        "serving",
        "maintenance_shutdown",
        "telemetry_shutdown",
    ]
    executor.shutdown.assert_called_once_with(wait=True)
