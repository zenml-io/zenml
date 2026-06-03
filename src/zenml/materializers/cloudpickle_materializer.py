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
"""Implementation of ZenML's cloudpickle materializer."""

import hashlib
import hmac
import os
from typing import Any, ClassVar, Optional, Tuple, Type

import cloudpickle

from zenml.enums import ArtifactType
from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils.io_utils import (
    read_file_contents_as_string,
    write_file_contents_as_string,
)

logger = get_logger(__name__)

DEFAULT_FILENAME = "artifact.pkl"
DEFAULT_PYTHON_VERSION_FILENAME = "python_version.txt"

# Chunk size used when streaming the stored artifact to compute its hash.
_HASH_CHUNK_SIZE = 65536


class CloudpickleMaterializer(BaseMaterializer):
    """Materializer using cloudpickle.

    This materializer can materialize (almost) any object, but does so in a
    non-reproducible way since artifacts cannot be loaded from other Python
    versions. It is recommended to use this materializer only as a last resort.

    That is also why it has `SKIP_REGISTRATION` set to True and is currently
    only used as a fallback materializer inside the materializer registry.
    """

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (object,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA
    SKIP_REGISTRATION: ClassVar[bool] = True

    def load(self, data_type: Type[Any]) -> Any:
        """Reads an artifact from a cloudpickle file.

        When a content hash was recorded for this artifact version, the stored
        file is checked against it before it is read back.

        Args:
            data_type: The data type of the artifact.

        Returns:
            The loaded artifact data.

        Raises:
            RuntimeError: If the stored file does not match the recorded content
                hash.
        """
        # validate python version
        source_python_version = self._load_python_version()
        current_python_version = Environment().python_version()
        if source_python_version != current_python_version:
            logger.warning(
                f"Your artifact was materialized under Python version "
                f"'{source_python_version}' but you are currently using "
                f"'{current_python_version}'. This might cause unexpected "
                "behavior since pickle is not reproducible across Python "
                "versions. Attempting to load anyway..."
            )

        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        with self.artifact_store.open(filepath, "rb") as fid:
            serialized_data = fid.read()

        expected_content_hash = self.expected_content_hash
        if expected_content_hash is not None:
            actual_content_hash = hashlib.sha256(serialized_data).hexdigest()
            if not hmac.compare_digest(
                actual_content_hash, expected_content_hash
            ):
                raise RuntimeError(
                    f"The artifact at '{self.uri}' does not match the content "
                    f"hash recorded for it and was not loaded."
                )

        return cloudpickle.loads(serialized_data)

    def _load_python_version(self) -> str:
        """Loads the Python version that was used to materialize the artifact.

        Returns:
            The Python version that was used to materialize the artifact.
        """
        filepath = os.path.join(self.uri, DEFAULT_PYTHON_VERSION_FILENAME)
        if os.path.exists(filepath):
            return read_file_contents_as_string(filepath)
        return "unknown"

    def save(self, data: Any) -> None:
        """Saves an artifact to a cloudpickle file.

        Args:
            data: The data to save.
        """
        # Log a warning if this materializer was not explicitly specified for
        # the given data type.
        if type(self) is CloudpickleMaterializer:
            logger.warning(
                f"No materializer is registered for type `{type(data)}`, so "
                "the default Pickle materializer was used. Pickle is not "
                "production ready and should only be used for prototyping as "
                "the artifacts cannot be loaded when running with a different "
                "Python version. Please consider implementing a custom "
                f"materializer for type `{type(data)}` according to the "
                "instructions at https://docs.zenml.io/concepts/artifacts/materializers"
            )

        # save python version for validation on loading
        self._save_python_version()

        # save data
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        with self.artifact_store.open(filepath, "wb") as fid:
            cloudpickle.dump(data, fid)

    def _save_python_version(self) -> None:
        """Saves the Python version used to materialize the artifact."""
        filepath = os.path.join(self.uri, DEFAULT_PYTHON_VERSION_FILENAME)
        current_python_version = Environment().python_version()
        write_file_contents_as_string(filepath, current_python_version)

    def compute_content_hash(self, data: Any) -> Optional[str]:
        """Compute a hash of the stored artifact file.

        The hash is taken over the bytes written to the store (not over `data`)
        so it can be recomputed on load without reading the object back.

        Args:
            data: The saved data. Unused; the hash is taken over the stored file.

        Returns:
            The hex-encoded SHA-256 of the stored file, or `None` if it cannot
            be read.
        """
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        try:
            digest = hashlib.sha256()
            with self.artifact_store.open(filepath, "rb") as fid:
                for chunk in iter(lambda: fid.read(_HASH_CHUNK_SIZE), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        except Exception as e:
            logger.warning(
                "Could not compute the content hash for the artifact at "
                "'%s'. (%s)",
                self.uri,
                e,
            )
            return None
