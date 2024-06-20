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


from datetime import datetime
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError


def _get_gcp_artifact_store(**kwargs):
    from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
        GCPArtifactStore,
    )
    from zenml.integrations.gcp.flavors.gcp_artifact_store_flavor import (
        GCPArtifactStoreConfig,
    )

    return GCPArtifactStore(
        name="",
        id=uuid4(),
        config=GCPArtifactStoreConfig(**kwargs),
        flavor="gcp",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_must_be_gcs_path():
    """Checks that a gcp artifact store can only be initialized with a gcspath."""
    with pytest.raises(ArtifactStoreInterfaceError):
        _get_gcp_artifact_store(path="/local/path")

    with pytest.raises(ArtifactStoreInterfaceError):
        _get_gcp_artifact_store(path="s3://local/path")

    artifact_store = _get_gcp_artifact_store(path="gs://mybucket")
    assert artifact_store.path == "gs://mybucket"
