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

from typing import Any, Callable, List, Optional
from unittest.mock import MagicMock, patch

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
