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


import pytest
from pydantic import ValidationError

from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
    GCPArtifactStore,
)


def test_must_be_gcs_path():
    """Checks must_be_gcs_path validator"""
    with pytest.raises(ValidationError):
        GCPArtifactStore(path="/local/path", repo_path="")

    with pytest.raises(ValidationError):
        GCPArtifactStore(path="s3://local/path", repo_path="")

    gcp_as = GCPArtifactStore(path="gs://mybucket", repo_path="")
    assert gcp_as.path == "gs://mybucket"
