#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from uuid import UUID

from zenml.enums import ArtifactType
from zenml.models.artifact_models import ArtifactRequestModel
from zenml.orchestrators.publish_utils import publish_output_artifacts


def test_publish_output_artifacts(clean_client):
    """Test that `register_output_artifacts()` registers new artifacts."""
    artifact_1 = ArtifactRequestModel(
        uri="some/uri/abc/",
        materializer="some_materializer",
        data_type="np.ndarray",
        type=ArtifactType.DATA,
        name="some_name",
        user=clean_client.active_user.id,
        workspace=clean_client.active_workspace.id,
    )
    artifact_2 = ArtifactRequestModel(
        uri="some/uri/def/",
        materializer="some_other_materializer",
        data_type="some data type",
        type=ArtifactType.DATA,
        name="some_name",
        user=clean_client.active_user.id,
        workspace=clean_client.active_workspace.id,
    )
    artifact_3 = ArtifactRequestModel(
        uri="some/uri/ghi/",
        materializer="some_model_materializer",
        data_type="some model type",
        type=ArtifactType.MODEL,
        name="some_name",
        user=clean_client.active_user.id,
        workspace=clean_client.active_workspace.id,
    )
    assert len(clean_client.list_artifacts()) == 0
    return_val = publish_output_artifacts({"output": artifact_1})
    assert len(clean_client.list_artifacts()) == 1
    assert isinstance(return_val, dict)
    assert len(return_val) == 1
    assert isinstance(return_val["output"], UUID)
    return_val = publish_output_artifacts({})
    assert len(clean_client.list_artifacts()) == 1
    assert return_val == {}
    return_val = publish_output_artifacts(
        {
            "arias_data": artifact_2,
            "arias_model": artifact_3,
        }
    )
    assert len(clean_client.list_artifacts()) == 3
    assert isinstance(return_val, dict)
    assert len(return_val) == 2
    assert isinstance(return_val["arias_data"], UUID)
    assert isinstance(return_val["arias_model"], UUID)
