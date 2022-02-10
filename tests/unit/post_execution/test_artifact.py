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
from contextlib import ExitStack as does_not_raise

import pytest

from zenml.post_execution.artifact import ArtifactView


def _create_artifact_view(materializer: str, data_type: str) -> ArtifactView:
    """Creates an artifact view with the given materializer and data type."""
    return ArtifactView(
        id_=0,
        type_="",
        uri="",
        materializer=materializer,
        data_type=data_type,
        metadata_store=None,
        parent_step_id=0,
    )


def test_reading_from_an_artifact_view_uses_the_specified_materializer_and_data_type(
    mocker,
):
    """Tests that reading from an artifact view uses the materializer and data
    type passed during initialization."""
    mocker.patch(
        "zenml.materializers.built_in_materializer.BuiltInMaterializer.handle_input"
    )
    artifact = _create_artifact_view(
        materializer="zenml.materializers.built_in_materializer.BuiltInMaterializer",
        data_type="builtins.int",
    )

    with does_not_raise():
        artifact.read()


def test_artifact_reading_fails_with_nonexisting_materializer(mocker):
    """Tests that reading from the artifact fails if the materializer class
    can't be imported."""
    mocker.patch(
        "zenml.materializers.built_in_materializer.BuiltInMaterializer.handle_input"
    )
    artifact = _create_artifact_view(
        materializer="some.nonexistent.Class", data_type="builtins.int"
    )

    with pytest.raises(ModuleNotFoundError):
        artifact.read()


def test_artifact_reading_fails_with_nonexisting_data_type(mocker):
    """Tests that reading from the artifact fails if the data type class
    can't be imported."""
    mocker.patch(
        "zenml.materializers.built_in_materializer.BuiltInMaterializer.handle_input"
    )
    artifact = _create_artifact_view(
        materializer="zenml.materializers.built_in_materializer.BuiltInMaterializer",
        data_type="some.nonexistent.Class",
    )

    with pytest.raises(ModuleNotFoundError):
        artifact.read()
