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


from zenml.artifacts.external_artifact import ExternalArtifact


def test_upload_by_value(sample_artifact_version_model, mocker):
    """Tests that `upload_by_value` works as expected for `value`."""
    ea = ExternalArtifact(value=1)
    assert ea._id is None
    mocker.patch(
        "zenml.artifacts.utils.save_artifact",
        return_value=sample_artifact_version_model,
    )
    ea.upload_by_value()
    assert ea._id is not None
    assert ea.value is None


def test_double_upload_by_value(sample_artifact_version_model, mocker):
    """Tests that `upload_by_value` works as expected for `value`."""
    ea = ExternalArtifact(value=1)
    assert ea._id is None
    mocker.patch(
        "zenml.artifacts.utils.save_artifact",
        return_value=sample_artifact_version_model,
    )
    ea.upload_by_value()
    assert ea._id is not None
    assert ea.value is None
    id_ = ea._id

    ea.upload_by_value()
    assert ea._id == id_
