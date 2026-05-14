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
import os
from datetime import datetime
from uuid import uuid4

import pytest

from zenml.artifact_stores import LocalArtifactStore, LocalArtifactStoreConfig
from zenml.artifact_stores.base_artifact_store import BaseArtifactStoreConfig
from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError


class TestBaseArtifactStoreConfig:
    class AriaArtifactStoreConfig(BaseArtifactStoreConfig):
        SUPPORTED_SCHEMES = {"aria://"}

    @pytest.mark.parametrize(
        "path",
        [
            "aria://my-bucket/my-folder/my-file.txt",
            "'aria://my-bucket/my-folder/my-file.txt'",
            "`aria://my-bucket/my-folder/my-file.txt`",
            '"aria://my-bucket/my-folder/my-file.txt"',
        ],
    )
    def test_valid_path(self, path):
        config = self.AriaArtifactStoreConfig(path=path)
        assert config.path == "aria://my-bucket/my-folder/my-file.txt"

    @pytest.mark.parametrize(
        "path",
        [
            "s3://my-bucket/my-folder/my-file.txt",
            "http://my-bucket/my-folder/my-file.txt",
        ],
    )
    def test_invalid_path(self, path):
        with pytest.raises(ArtifactStoreInterfaceError):
            self.AriaArtifactStoreConfig(path=path)


def test_optional_object_helpers_fall_back_to_filesystem_methods(tmp_path):
    """Tests optional artifact-store helper fallbacks on a local store."""
    local_artifact_store = LocalArtifactStore(
        name="test-artifact-store",
        id=uuid4(),
        config=LocalArtifactStoreConfig(path=str(tmp_path)),
        flavor="local",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    root = os.path.join(local_artifact_store.path, "objects")
    nested = os.path.join(root, "nested")
    local_artifact_store.makedirs(nested)

    first_path = os.path.join(root, "first.txt")
    second_path = os.path.join(nested, "second.txt")
    with local_artifact_store.open(first_path, "w") as file:
        file.write("abcdef")
    with local_artifact_store.open(second_path, "w") as file:
        file.write("nested")

    non_recursive_objects = list(local_artifact_store.list_objects(root))
    recursive_objects = list(
        local_artifact_store.list_objects(root, recursive=True)
    )

    assert [obj.relative_path for obj in non_recursive_objects] == [
        "first.txt"
    ]
    assert [obj.relative_path for obj in recursive_objects] == [
        "first.txt",
        "nested/second.txt",
    ]
    assert non_recursive_objects[0].size == 6
    assert (
        local_artifact_store.read_range(first_path, offset=1, length=3)
        == b"bcd"
    )
    assert local_artifact_store.read_range(first_path, offset=3) == b"def"

    missing_path = os.path.join(root, "missing.txt")
    result = local_artifact_store.delete_objects([first_path, missing_path])

    assert result.deleted_paths == [first_path]
    assert [failure.path for failure in result.failures] == [missing_path]
    assert not local_artifact_store.exists(first_path)
    assert local_artifact_store.exists(second_path)
