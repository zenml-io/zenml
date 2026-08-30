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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Authorization contract for execution archive endpoints."""

from typing import cast
from uuid import uuid4

from pytest_mock import MockerFixture

from zenml.zen_server.auth import AuthContext
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.routers import execution_archive_endpoints


def test_archive_authorization_uses_admin_fallback_and_scoped_rbac(
    mocker: MockerFixture,
) -> None:
    """Delegated RBAC replaces, rather than supplements, global admin."""
    project_id = uuid4()
    root_run_id = uuid4()
    auth_context = cast(AuthContext, mocker.Mock())
    auth_context.user.is_admin = False
    admin_fallback = mocker.patch.object(
        execution_archive_endpoints, "verify_admin_status_if_no_rbac"
    )
    permission = mocker.patch.object(
        execution_archive_endpoints, "verify_permission"
    )

    execution_archive_endpoints._authorize_execution_archive(
        auth_context,
        action="export execution history",
        permission=Action.UPDATE,
        project_id=project_id,
        root_run_id=root_run_id,
    )

    admin_fallback.assert_called_once_with(False, "export execution history")
    permission.assert_called_once_with(
        resource_type=ResourceType.PIPELINE_RUN,
        action=Action.UPDATE,
        resource_id=root_run_id,
        project_id=project_id,
    )
