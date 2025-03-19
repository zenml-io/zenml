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
from uuid import uuid4

from zenml.enums import ArtifactType
from zenml.models import (
    ModelResponse,
    ModelResponseBody,
    ModelResponseMetadata,
    ModelVersionResponse,
    ModelVersionResponseBody,
    ModelVersionResponseMetadata,
)


def test_model_version_response_artifact_fetching(
    clean_client, mocker, sample_project_model
):
    """Test artifact fetching from a model version response."""
    mock_list_artifact_versions = mocker.patch.object(
        type(clean_client),
        "list_artifact_versions",
    )

    model = ModelResponse(
        id=uuid4(),
        name="model",
        body=ModelResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            tags=[],
        ),
        metadata=ModelResponseMetadata(
            project=sample_project_model,
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
        ),
        metadata=ModelVersionResponseMetadata(
            project=sample_project_model,
        ),
    )

    artifact_name = "artifact_name"
    version_name = "version_name"

    mv.get_artifact(artifact_name, version_name)
    mock_list_artifact_versions.assert_called_once_with(
        sort_by="desc:created",
        size=1,
        artifact=artifact_name,
        version=version_name,
        model_version_id=mv.id,
        type=None,
        hydrate=True,
    )
    mock_list_artifact_versions.reset_mock()

    mv.get_data_artifact(artifact_name, version_name)
    mock_list_artifact_versions.assert_called_once_with(
        sort_by="desc:created",
        size=1,
        artifact=artifact_name,
        version=version_name,
        model_version_id=mv.id,
        type=ArtifactType.DATA,
        hydrate=True,
    )
    mock_list_artifact_versions.reset_mock()

    mv.get_model_artifact(artifact_name, version_name)
    mock_list_artifact_versions.assert_called_once_with(
        sort_by="desc:created",
        size=1,
        artifact=artifact_name,
        version=version_name,
        model_version_id=mv.id,
        type=ArtifactType.MODEL,
        hydrate=True,
    )
    mock_list_artifact_versions.reset_mock()

    mv.get_deployment_artifact(artifact_name, version_name)
    mock_list_artifact_versions.assert_called_once_with(
        sort_by="desc:created",
        size=1,
        artifact=artifact_name,
        version=version_name,
        model_version_id=mv.id,
        type=ArtifactType.SERVICE,
        hydrate=True,
    )
