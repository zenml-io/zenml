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
"""Only-load materializer for directories."""

import os
import tempfile
from pathlib import Path
from typing import Any, ClassVar, Tuple, Type

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class PreexistingDataMaterializer(BaseMaterializer):
    """Materializer to load directories from the artifact store.

    This materializer is very special, since it do not implement save
    logic at all. The save of the data to some URI inside the artifact store
    shall happen outside and is in user's responsibility.

    This materializer solely supports the `register_artifact` function.
    """

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (Path,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA
    SKIP_REGISTRATION: ClassVar[bool] = True

    def load(self, data_type: Type[Any]) -> Any:
        """Copy the artifact file(s) to a local temp directory.

        Args:
            data_type: Unused.

        Returns:
            Path to the local directory that contains the artifact files.
        """
        directory = tempfile.mkdtemp(prefix="zenml-artifact")
        self.register_local_directory_cleanup(directory)
        if fileio.isdir(self.uri):
            self._copy_directory(src=self.uri, dst=directory)
            return Path(directory)
        else:
            dst = os.path.join(directory, os.path.split(self.uri)[-1])
            fileio.copy(src=self.uri, dst=dst)
            return Path(dst)

    def save(self, data: Any) -> None:
        """Store the directory in the artifact store.

        Args:
            data: Path to a local directory to store.

        Raises:
            NotImplementedError: Always
        """
        raise NotImplementedError(
            "`PreexistingDataMaterializer` can only be used in the "
            "context of `register_artifact` function, "
            "which expects the data to be already properly saved in "
            "the Artifact Store, thus `save` logic makes no sense here."
        )

    @staticmethod
    def _copy_directory(src: str, dst: str) -> None:
        """Recursively copy a directory.

        Args:
            src: The directory to copy.
            dst: Where to copy the directory to.
        """
        for src_dir, _, files in fileio.walk(src):
            src_dir_ = str(src_dir)
            dst_dir = str(os.path.join(dst, os.path.relpath(src_dir_, src)))
            fileio.makedirs(dst_dir)

            for file in files:
                file_ = str(file)
                src_file = os.path.join(src_dir_, file_)
                dst_file = os.path.join(dst_dir, file_)
                fileio.copy(src_file, dst_file)
