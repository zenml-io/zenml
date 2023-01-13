#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import datetime
from contextlib import ExitStack as does_not_raise
from uuid import uuid4

import pytest

from zenml.enums import ArtifactType
from zenml.models import ArtifactResponseModel
from zenml.models.project_models import ProjectResponseModel
from zenml.models.user_models import UserResponseModel
from zenml.post_execution.artifact import ArtifactView


def _create_artifact_view(
    materializer: str,
    data_type: str,
    project: ProjectResponseModel,
    user: UserResponseModel,
) -> ArtifactView:
    """Creates an artifact view with the given materializer and data type."""
    return ArtifactView(
        ArtifactResponseModel(
            id=uuid4(),
            type=ArtifactType.DATA,
            uri="",
            materializer=materializer,
            data_type=data_type,
            name="",
            created=datetime.datetime.now(),
            updated=datetime.datetime.now(),
            project=project,
            user=user,
        )
    )


def test_reading_from_an_artifact_view_uses_the_specified_materializer_and_data_type(
    mocker, sample_project_model, sample_user_model
):
    """Tests that reading from an artifact view uses the materializer and data type passed during initialization."""
    mocker.patch(
        "zenml.materializers.built_in_materializer.BuiltInMaterializer.load"
    )
    artifact = _create_artifact_view(
        materializer="zenml.materializers.built_in_materializer.BuiltInMaterializer",
        data_type="builtins.int",
        project=sample_project_model,
        user=sample_user_model,
    )

    with does_not_raise():
        artifact.read()


def test_artifact_reading_fails_with_nonexisting_materializer(
    mocker, sample_project_model, sample_user_model
):
    """Tests that reading from the artifact fails if the materializer class can't be imported."""
    mocker.patch(
        "zenml.materializers.built_in_materializer.BuiltInMaterializer.load"
    )
    artifact = _create_artifact_view(
        materializer="some.nonexistent.Class",
        data_type="builtins.int",
        project=sample_project_model,
        user=sample_user_model,
    )

    with pytest.raises(ModuleNotFoundError):
        artifact.read()


def test_artifact_reading_fails_with_nonexisting_data_type(
    mocker, sample_project_model, sample_user_model
):
    """Tests that reading from the artifact fails if the data type class can't be imported."""
    mocker.patch(
        "zenml.materializers.built_in_materializer.BuiltInMaterializer.load"
    )
    artifact = _create_artifact_view(
        materializer="zenml.materializers.built_in_materializer.BuiltInMaterializer",
        data_type="some.nonexistent.Class",
        project=sample_project_model,
        user=sample_user_model,
    )

    with pytest.raises(ModuleNotFoundError):
        artifact.read()
