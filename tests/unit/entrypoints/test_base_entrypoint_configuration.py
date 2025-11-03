#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from uuid import uuid4

import pytest

from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.models import PipelineRequest, PipelineSnapshotRequest


class StubEntrypointConfiguration(BaseEntrypointConfiguration):
    def run(self) -> None:
        pass


def test_calling_entrypoint_configuration_with_invalid_snapshot_id():
    """Tests that a valid snapshot ID is required as argument."""
    with pytest.raises(ValueError):
        BaseEntrypointConfiguration.get_entrypoint_arguments()

    with pytest.raises(ValueError):
        BaseEntrypointConfiguration.get_entrypoint_arguments(
            snapshot_id="not_a_uuid"
        )

    with does_not_raise():
        BaseEntrypointConfiguration.get_entrypoint_arguments(
            snapshot_id=uuid4()
        )


def test_loading_the_snapshot(clean_client):
    """Tests loading the snapshot by ID."""
    pipeline = clean_client.zen_store.create_pipeline(
        PipelineRequest(
            name="pipeline",
            project=clean_client.active_project.id,
        )
    )
    request = PipelineSnapshotRequest(
        user=clean_client.active_user.id,
        project=clean_client.active_project.id,
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        stack=clean_client.active_stack.id,
        client_version="0.12.3",
        server_version="0.12.3",
        pipeline=pipeline.id,
    )

    snapshot = clean_client.zen_store.create_snapshot(request)

    entrypoint_config = StubEntrypointConfiguration(
        arguments=["--snapshot_id", str(snapshot.id)]
    )

    assert entrypoint_config.snapshot == snapshot
