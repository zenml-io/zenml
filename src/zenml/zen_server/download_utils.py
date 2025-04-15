#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Utility functions for downloading artifacts."""

import os
import tarfile
import tempfile
from typing import (
    TYPE_CHECKING,
)

from zenml.artifacts.utils import _load_artifact_store
from zenml.exceptions import (
    IllegalOperationError,
)
from zenml.models import (
    ArtifactVersionResponse,
)
from zenml.zen_server.utils import server_config, zen_store

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore


def verify_artifact_is_downloadable(
    artifact: "ArtifactVersionResponse",
) -> "BaseArtifactStore":
    """Verify that the given artifact is downloadable.

    Args:
        artifact: The artifact to verify.

    Raises:
        IllegalOperationError: If the artifact is too large to be archived.
        KeyError: If the artifact store is not found or the artifact URI does
            not exist.

    Returns:
        The artifact store.
    """
    if not artifact.artifact_store_id:
        raise KeyError(
            f"Artifact '{artifact.id}' cannot be downloaded because the "
            "underlying artifact store was deleted."
        )

    artifact_store = _load_artifact_store(
        artifact_store_id=artifact.artifact_store_id, zen_store=zen_store()
    )

    if not artifact_store.exists(artifact.uri):
        raise KeyError(f"The artifact URI '{artifact.uri}' does not exist.")

    size = artifact_store.size(artifact.uri)
    max_download_size = server_config().file_download_size_limit

    if size and size > max_download_size:
        raise IllegalOperationError(
            f"The artifact '{artifact.id}' is too large to be downloaded. "
            f"The maximum download size allowed by your ZenML server is "
            f"{max_download_size} bytes."
        )

    return artifact_store


def create_artifact_archive(
    artifact: "ArtifactVersionResponse",
) -> str:
    """Create an archive of the given artifact.

    Args:
        artifact: The artifact to archive.

    Returns:
        The path to the created archive.
    """
    artifact_store = verify_artifact_is_downloadable(artifact)

    def _prepare_tarinfo(path: str) -> tarfile.TarInfo:
        archive_path = os.path.relpath(path, artifact.uri)
        tarinfo = tarfile.TarInfo(name=archive_path)
        if size := artifact_store.size(path):
            tarinfo.size = size
        return tarinfo

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        with tarfile.open(fileobj=temp_file, mode="w:gz") as tar:
            if artifact_store.isdir(artifact.uri):
                for dir, _, files in artifact_store.walk(artifact.uri):
                    dir = dir.decode() if isinstance(dir, bytes) else dir
                    dir_info = tarfile.TarInfo(
                        name=os.path.relpath(dir, artifact.uri)
                    )
                    dir_info.type = tarfile.DIRTYPE
                    dir_info.mode = 0o755
                    tar.addfile(dir_info)

                    for file in files:
                        file = (
                            file.decode() if isinstance(file, bytes) else file
                        )
                        path = os.path.join(dir, file)
                        tarinfo = _prepare_tarinfo(path)
                        with artifact_store.open(path, "rb") as f:
                            tar.addfile(tarinfo, fileobj=f)
            else:
                tarinfo = _prepare_tarinfo(artifact.uri)
                with artifact_store.open(artifact.uri, "rb") as f:
                    tar.addfile(tarinfo, fileobj=f)

        return temp_file.name
