#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
from contextlib import ExitStack as does_not_raise
from datetime import datetime
from uuid import uuid4

from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.models import (
    PipelineBuildResponse,
    PipelineBuildResponseBody,
)
from zenml.zen_server.pipeline_execution.utils import (
    snapshot_request_from_source_snapshot,
)


def test_creating_snapshot_request_from_template(
    clean_client_with_run, mocker
):
    mocker.patch(
        "zenml.zen_server.pipeline_execution.utils.zen_store",
        return_value=clean_client_with_run.zen_store,
    )

    snapshots = clean_client_with_run.list_snapshots(
        named_only=False, hydrate=True
    )
    assert len(snapshots) == 1

    snapshot = snapshots[0]

    build = PipelineBuildResponse(
        id=uuid4(),
        body=PipelineBuildResponseBody(
            user_id=snapshot.user_id,
            project_id=snapshot.project_id,
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        ),
    )
    snapshot.resources.build = build

    with does_not_raise():
        snapshot_request_from_source_snapshot(
            source_snapshot=snapshot,
            config=PipelineRunConfiguration(),
        )
