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

from typing import Any, ClassVar, Optional
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from zenml.artifacts.external_artifact import ExternalArtifact

GLOBAL_ARTIFACT_ID = uuid4()


class MockZenmlClient:
    class Client:
        ARTIFACT_STORE_ID: ClassVar[int] = 42

        class MockArtifactResponse:
            def __init__(self, name, id=GLOBAL_ARTIFACT_ID):
                self.artifact_store_id = 42
                self.name = name
                self.id = id

        class MockPipelineResponse:
            def __init__(self):
                self.last_successful_run = MagicMock()
                self.last_successful_run.artifacts = [
                    MockZenmlClient.Client.MockArtifactResponse("foo"),
                    MockZenmlClient.Client.MockArtifactResponse("bar"),
                ]

        def __init__(self):
            self.active_stack = MagicMock()
            self.active_stack.artifact_store.id = self.ARTIFACT_STORE_ID
            self.active_stack.artifact_store.path = "foo"

        def get_artifact(self, *args, **kwargs):
            if len(args):
                return MockZenmlClient.Client.MockArtifactResponse(
                    "foo", args[0]
                )
            else:
                return MockZenmlClient.Client.MockArtifactResponse("foo")

        def get_pipeline(self, *args, **kwargs):
            return MockZenmlClient.Client.MockPipelineResponse()


@pytest.mark.parametrize(
    argnames="value,id,pipeline_name,artifact_name,model_name,model_version,model_artifact_name,exception_start",
    argvalues=[
        [1, None, None, None, None, None, None, ""],
        [None, uuid4(), None, None, None, None, None, ""],
        [None, None, "foo", "bar", None, None, None, ""],
        [None, None, None, None, "foo", "bar", "artifact", ""],
        [None, None, None, None, None, None, None, "Either a value,"],
        [1, uuid4(), None, None, None, None, None, "Only a value,"],
        [None, uuid4(), "foo", "bar", None, None, None, "Only a value,"],
        [1, None, "foo", "bar", None, None, None, "Only a value,"],
        [1, None, None, None, "foo", "bar", "artifact", "Only a value,"],
        [None, uuid4(), None, None, "foo", "bar", "artifact", "Only a value,"],
        [None, None, "foo", "bar", "foo", "bar", "artifact", "Only a value,"],
        [
            None,
            None,
            "foo",
            None,
            None,
            None,
            None,
            "`pipeline_name` and `artifact_name`",
        ],
        [
            None,
            None,
            None,
            "bar",
            None,
            None,
            None,
            "`pipeline_name` and `artifact_name`",
        ],
    ],
    ids=[
        "good_by_value",
        "good_by_id",
        "good_by_pipeline_artifact",
        "good_by_model",
        "bad_all_none",
        "bad_id_and_value",
        "bad_id_and_pipeline_artifact",
        "bad_value_and_pipeline_artifact",
        "bad_value_and_model",
        "bad_id_and_model",
        "bad_pipeline_artifact_and_model",
        "bad_only_pipeline",
        "bad_only_artifact",
    ],
)
def test_external_artifact_init(
    value: Optional[Any],
    id: Optional[UUID],
    pipeline_name: Optional[str],
    artifact_name: Optional[str],
    model_name: Optional[str],
    model_version: Optional[str],
    model_artifact_name: Optional[str],
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
                model_name=model_name,
                model_version=model_version,
                model_artifact_name=model_artifact_name,
            )
    else:
        ExternalArtifact(
            value=value,
            id=id,
            pipeline_name=pipeline_name,
            artifact_name=artifact_name,
            model_name=model_name,
            model_version=model_version,
            model_artifact_name=model_artifact_name,
        )


@patch("zenml.artifacts.external_artifact.fileio")
def test_upload_if_necessary_by_value(mocked_fileio):
    mocked_fileio.exists.return_value = False
    ea = ExternalArtifact(value=1)
    assert ea.id is None
    with patch.dict(
        "sys.modules",
        {
            "zenml.utils.artifact_utils": MagicMock(),
            "zenml.client": MockZenmlClient,
        },
    ):
        ea.upload_if_necessary()
    assert ea.id is not None
    assert ea.value is None
    assert ea.pipeline_name is None
    assert ea.artifact_name is None


def test_upload_if_necessary_by_id():
    ea = ExternalArtifact(id=GLOBAL_ARTIFACT_ID)
    assert ea.value is None
    assert ea.pipeline_name is None
    assert ea.artifact_name is None
    assert ea.id is not None
    with patch.dict(
        "sys.modules",
        {
            "zenml.utils.artifact_utils": MagicMock(),
            "zenml.client": MockZenmlClient,
        },
    ):
        assert ea.upload_if_necessary() == GLOBAL_ARTIFACT_ID


def test_upload_if_necessary_by_pipeline_and_artifact():
    ea = ExternalArtifact(pipeline_name="foo", artifact_name="bar")
    assert ea.value is None
    assert ea.pipeline_name is not None
    assert ea.artifact_name is not None
    assert ea.id is None
    with patch.dict(
        "sys.modules",
        {
            "zenml.utils.artifact_utils": MagicMock(),
            "zenml.client": MockZenmlClient,
        },
    ):
        assert ea.upload_if_necessary() == GLOBAL_ARTIFACT_ID
    assert ea.id == GLOBAL_ARTIFACT_ID


def test_upload_if_necessary_by_pipeline_and_artifact_other_artifact_store():
    # mocked_client.return_value = lambda: MockClient(artifact_store_id=45)
    with pytest.raises(
        RuntimeError,
        match=r"The artifact bar \(ID: " + str(GLOBAL_ARTIFACT_ID) + r"\)",
    ):
        try:
            old_id = MockZenmlClient.Client.ARTIFACT_STORE_ID
            MockZenmlClient.Client.ARTIFACT_STORE_ID = 45
            with patch.dict(
                "sys.modules",
                {
                    "zenml.utils.artifact_utils": MagicMock(),
                    "zenml.client": MockZenmlClient,
                },
            ):
                ExternalArtifact(
                    pipeline_name="foo", artifact_name="bar"
                ).upload_if_necessary()
        finally:
            MockZenmlClient.Client.ARTIFACT_STORE_ID = old_id


def test_upload_if_necessary_by_pipeline_and_artifact_name_not_found():
    with pytest.raises(RuntimeError, match="Artifact with name `foobar`"):
        with patch.dict(
            "sys.modules",
            {
                "zenml.utils.artifact_utils": MagicMock(),
                "zenml.client": MockZenmlClient,
            },
        ):
            ExternalArtifact(
                pipeline_name="foo", artifact_name="foobar"
            ).upload_if_necessary()
