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

from zenml.artifact_stores.base_artifact_store import BaseArtifactStoreConfig
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
