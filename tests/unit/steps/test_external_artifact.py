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

from typing import Any, Optional
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from zenml.steps.external_artifact import ExternalArtifact


class MockClient:
    class MockArtifactResponse:
        def __init__(self, name):
            self.artifact_store_id = 42
            self.name = name
            self.id = 123

    class MockPipelineResponse:
        def __init__(self):
            self.last_successful_run = MagicMock()
            self.last_successful_run.artifacts = [
                MockClient.MockArtifactResponse("foo"),
                MockClient.MockArtifactResponse("bar"),
            ]

    def __init__(self, artifact_store_id=42):
        self.active_stack = MagicMock()
        self.active_stack.artifact_store.id = artifact_store_id
        self.active_stack.artifact_store.path = "foo"

    def get_artifact(self, *args, **kwargs):
        return MockClient.MockArtifactResponse("foo")

    def get_pipeline(self, *args, **kwargs):
        return MockClient.MockPipelineResponse()


@pytest.mark.parametrize(
    argnames="value,id,pipeline_name,artifact_name,exception_start",
    argvalues=[
        [1, None, None, None, ""],
        [None, uuid4(), None, None, ""],
        [None, None, "foo", "bar", ""],
        [None, None, None, None, "Either a value,"],
        [1, uuid4(), None, None, "Only a value,"],
        [None, uuid4(), "foo", "bar", "Only a value,"],
        [1, None, "foo", "bar", "Only a value,"],
        [None, None, "foo", None, "`pipeline_name` and `artifact_name`"],
        [None, None, None, "bar", "`pipeline_name` and `artifact_name`"],
    ],
    ids=[
        "good_by_value",
        "good_by_id",
        "good_by_pipeline_artifact",
        "bad_all_none",
        "bad_id_and_value",
        "bad_id_and_pipeline_artifact",
        "bad_value_and_pipeline_artifact",
        "bad_only_pipeline",
        "bad_only_artifact",
    ],
)
def test_external_artifact_init(
    value: Optional[Any],
    id: Optional[UUID],
    pipeline_name: Optional[str],
    artifact_name: Optional[str],
    exception_start: str,
):
    """Tests that initialization logic of `ExternalArtifact` works expectedly."""
    if exception_start:
        with pytest.raises(ValueError, match=exception_start):
            ExternalArtifact(
                value=value,
                id=id,
                pipeline_name=pipeline_name,
                artifact_name=artifact_name,
            )
    else:
        ExternalArtifact(
            value=value,
            id=id,
            pipeline_name=pipeline_name,
            artifact_name=artifact_name,
        )


@patch("zenml.steps.external_artifact.Client")
@patch("zenml.steps.external_artifact.fileio")
@patch("zenml.steps.external_artifact.artifact_utils")
def test_upload_if_necessary_by_value(
    mocked_zenml_client,
    mocked_fileio,
    mocked_artifact_utils,
):
    mocked_fileio.exists.return_value = False
    ea = ExternalArtifact(value=1)
    assert ea._id is None
    ea.upload_if_necessary()
    assert ea._id is not None
    assert ea._value is not None
    assert ea._pipeline_name is None
    assert ea._artifact_name is None


@pytest.mark.skip
@patch("zenml.steps.external_artifact.Client")
def test_upload_if_necessary_by_id(mocked_zenml_client):
    mocked_zenml_client.return_value = MockClient()
    ea = ExternalArtifact(id=123)
    assert ea._value is None
    assert ea._pipeline_name is None
    assert ea._artifact_name is None
    assert ea._id is not None
    assert ea.upload_if_necessary() == 123


@patch("zenml.steps.external_artifact.Client")
def test_upload_if_necessary_by_pipeline_and_artifact(
    mocked_zenml_client,
):
    mocked_zenml_client.return_value = MockClient()
    ea = ExternalArtifact(pipeline_name="foo", artifact_name="bar")
    assert ea._value is None
    assert ea._pipeline_name is not None
    assert ea._artifact_name is not None
    assert ea._id is None
    assert ea.upload_if_necessary() == 123
    assert ea._id == 123


@patch("zenml.steps.external_artifact.Client")
def test_upload_if_necessary_by_pipeline_and_artifact_other_artifact_store(
    mocked_zenml_client,
):
    mocked_zenml_client.return_value = MockClient(artifact_store_id=45)
    with pytest.raises(RuntimeError, match=r"The artifact bar \(ID: 123\)"):
        ExternalArtifact(
            pipeline_name="foo", artifact_name="bar"
        ).upload_if_necessary()


@patch("zenml.steps.external_artifact.Client")
def test_upload_if_necessary_by_pipeline_and_artifact_name_not_found(
    mocked_zenml_client,
):
    mocked_zenml_client.return_value = MockClient()
    with pytest.raises(RuntimeError, match="Artifact with name `foobar`"):
        ExternalArtifact(
            pipeline_name="foo", artifact_name="foobar"
        ).upload_if_necessary()
