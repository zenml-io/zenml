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
"""Tests for the snapshot replacement permission check."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.zen_server.rbac.models import Action
from zenml.zen_server.routers import pipeline_snapshot_endpoints


@pytest.mark.parametrize("renaming_itself", [False, True])
def test_replace_requires_delete_on_displaced_snapshot(
    renaming_itself: bool,
) -> None:
    """Replacing a name needs DELETE on the snapshot that currently holds it."""
    existing = MagicMock(id=uuid4())
    store = MagicMock()
    store.list_snapshots.return_value.items = [existing]

    with (
        patch.object(
            pipeline_snapshot_endpoints, "zen_store", return_value=store
        ),
        patch.object(
            pipeline_snapshot_endpoints, "verify_permission_for_model"
        ) as verify,
    ):
        pipeline_snapshot_endpoints.verify_replace_permission(
            project_id=uuid4(),
            pipeline_id=uuid4(),
            name="shared",
            exclude_snapshot_id=existing.id if renaming_itself else None,
        )

    if renaming_itself:
        verify.assert_not_called()
    else:
        verify.assert_called_once_with(existing, action=Action.DELETE)
