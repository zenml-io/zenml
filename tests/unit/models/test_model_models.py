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

from datetime import datetime
from typing import ClassVar
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.models import (
    ModelResponse,
    ModelResponseBody,
    ModelResponseMetadata,
    ModelVersionResponse,
    ModelVersionResponseBody,
    ModelVersionResponseMetadata,
)

GLOBAL_ARTIFACT_VERSION_ID = uuid4()


class MockZenmlClient:
    class Client:
        ARTIFACT_STORE_ID: ClassVar[int] = 42

        class MockArtifactVersionResponse:
            def __init__(self, name, id=GLOBAL_ARTIFACT_VERSION_ID):
                self.artifact_store_id = 42
                self.name = name
                self.id = id

        class MockPipelineRunResponse:
            def __init__(self):
                self.name = "foo"
                self.artifact_versions = [
                    MockZenmlClient.Client.MockArtifactVersionResponse("foo"),
                    MockZenmlClient.Client.MockArtifactVersionResponse("bar"),
                ]

        class MockPipelineResponse:
            def __init__(self):
                self.last_successful_run = (
                    MockZenmlClient.Client.MockPipelineRunResponse()
                )

        def __init__(self):
            self.active_stack = MagicMock()
            self.active_stack.artifact_store.id = self.ARTIFACT_STORE_ID
            self.active_stack.artifact_store.path = "foo"

        def get_artifact_version(self, *args, **kwargs):
            if len(args):
                return MockZenmlClient.Client.MockArtifactVersionResponse(
                    "foo", args[0]
                )
            else:
                return MockZenmlClient.Client.MockArtifactVersionResponse(
                    "foo"
                )

        def get_pipeline(self, *args, **kwargs):
            return MockZenmlClient.Client.MockPipelineResponse()

        def get_pipeline_run(self, *args, **kwargs):
            return MockZenmlClient.Client.MockPipelineRunResponse()


ARTIFACT_VERSION_IDS = [uuid4(), uuid4()]


@pytest.mark.parametrize(
    "artifact_object_ids,query_name,query_version,expected",
    (
        (
            {"artifact": {"1": ARTIFACT_VERSION_IDS[0]}},
            "artifact",
            None,
            ARTIFACT_VERSION_IDS[0],
        ),
        (
            {
                "artifact": {
                    "1": ARTIFACT_VERSION_IDS[0],
                    "2": ARTIFACT_VERSION_IDS[1],
                }
            },
            "artifact",
            None,
            ARTIFACT_VERSION_IDS[1],
        ),
        (
            {
                "artifact": {
                    "1": ARTIFACT_VERSION_IDS[0],
                    "2": ARTIFACT_VERSION_IDS[1],
                }
            },
            "artifact",
            "1",
            ARTIFACT_VERSION_IDS[0],
        ),
        (
            {},
            "artifact",
            None,
            None,
        ),
    ),
    ids=[
        "No collision",
        "Latest version",
        "Specific version",
        "Not found",
    ],
)
def test_getters(
    artifact_object_ids,
    query_name,
    query_version,
    expected,
    sample_workspace_model,
):
    """Test that the getters work as expected."""
    with patch.dict(
        "sys.modules",
        {
            "zenml.client": MockZenmlClient,
        },
    ):
        model = ModelResponse(
            id=uuid4(),
            name="model",
            body=ModelResponseBody(
                created=datetime.now(),
                updated=datetime.now(),
                tags=[],
            ),
            metadata=ModelResponseMetadata(
                workspace=sample_workspace_model,
            ),
        )
        mv = ModelVersionResponse(
            id=uuid4(),
            name="foo",
            body=ModelVersionResponseBody(
                created=datetime.now(),
                updated=datetime.now(),
                model=model,
                number=-1,
                data_artifact_ids=artifact_object_ids,
            ),
            metadata=ModelVersionResponseMetadata(
                workspace=sample_workspace_model,
            ),
        )
        if expected != "RuntimeError":
            got = mv.get_data_artifact(
                name=query_name,
                version=query_version,
            )
            if got is not None:
                assert got.id == expected
            else:
                assert expected is None
        else:
            with pytest.raises(RuntimeError):
                mv.get_data_artifact(
                    name=query_name,
                    version=query_version,
                )
