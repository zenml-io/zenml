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
"""Great Expectations store plugin for ZenML."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

from great_expectations.data_context.store.tuple_store_backend import (  # type: ignore[import-untyped]
    TupleStoreBackend,
    filter_properties_dict,
)
from great_expectations.exceptions import (  # type: ignore[import-untyped]
    InvalidKeyError,
    StoreBackendError,
)

from zenml.client import Client
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils

logger = get_logger(__name__)


class ZenMLArtifactStoreBackend(TupleStoreBackend):  # type: ignore[misc]
    """Great Expectations store backend that uses the active ZenML Artifact Store as a store."""

    def __init__(
        self,
        prefix: str = "",
        **kwargs: Any,
    ) -> None:
        """Create a Great Expectations ZenML store backend instance.

        Args:
            prefix: Subpath prefix to use for this store backend.
            kwargs: Additional keyword arguments passed by the Great Expectations
                core. These are transparently passed to the `TupleStoreBackend`
                constructor.
        """
        super().__init__(**kwargs)

        client = Client()
        artifact_store = client.active_stack.artifact_store
        self.root_path = os.path.join(
            artifact_store.path, "great_expectations"
        )

        # extract the protocol used in the artifact store root path
        protocols = [
            scheme
            for scheme in artifact_store.config.SUPPORTED_SCHEMES
            if self.root_path.startswith(scheme)
        ]
        if protocols:
            self.proto = protocols[0]
        else:
            self.proto = ""

        if prefix:
            if self.platform_specific_separator:
                prefix = prefix.strip(os.sep)
            prefix = prefix.strip("/")
        self.prefix = prefix

        # Initialize with store_backend_id if not part of an HTMLSiteStore
        if not self._suppress_store_backend_id:
            _ = self.store_backend_id

        self._config = {
            "prefix": prefix,
            "module_name": self.__class__.__module__,
            "class_name": self.__class__.__name__,
        }
        self._config.update(kwargs)
        filter_properties_dict(
            properties=self._config, clean_falsy=True, inplace=True
        )

    def _build_object_path(
        self, key: Tuple[str, ...], is_prefix: bool = False
    ) -> str:
        """Build a filepath corresponding to an object key.

        Args:
            key: Great Expectation object key.
            is_prefix: If True, the key will be interpreted as a prefix instead
                of a full key identifier.

        Returns:
            The file path pointing to where the object is stored.
        """
        if not isinstance(key, tuple):
            key = key.to_tuple()
        if not is_prefix:
            object_relative_path = self._convert_key_to_filepath(key)
        elif key:
            object_relative_path = os.path.join(*key)
        else:
            object_relative_path = ""
        if self.prefix:
            object_key = os.path.join(self.prefix, object_relative_path)
        else:
            object_key = object_relative_path
        return os.path.join(self.root_path, object_key)

    def _get(self, key: Tuple[str, ...]) -> str:
        """Get the value of an object from the store.

        Args:
            key: object key identifier.

        Raises:
            InvalidKeyError: if the key doesn't point to an existing object.

        Returns:
            str: the object's contents
        """
        filepath: str = self._build_object_path(key)
        if fileio.exists(filepath):
            contents = io_utils.read_file_contents_as_string(filepath).rstrip(
                "\n"
            )
        else:
            raise InvalidKeyError(
                f"Unable to retrieve object from {self.__class__.__name__} with "
                f"the following Key: {str(filepath)}"
            )
        return contents

    def _set(self, key: Tuple[str, ...], value: str, **kwargs: Any) -> str:
        """Set the value of an object in the store.

        Args:
            key: object key identifier.
            value: object value to set.
            kwargs: additional keyword arguments (ignored).

        Returns:
            The file path where the object was stored.
        """
        filepath: str = self._build_object_path(key)
        if not io_utils.is_remote(filepath):
            parent_dir = str(Path(filepath).parent)
            os.makedirs(parent_dir, exist_ok=True)

        with fileio.open(filepath, "wb") as outfile:
            if isinstance(value, str):
                outfile.write(value.encode("utf-8"))
            else:
                outfile.write(value)
        return filepath

    def _move(
        self,
        source_key: Tuple[str, ...],
        dest_key: Tuple[str, ...],
        **kwargs: Any,
    ) -> None:
        """Associate an object with a different key in the store.

        Args:
            source_key: current object key identifier.
            dest_key: new object key identifier.
            kwargs: additional keyword arguments (ignored).
        """
        source_path = self._build_object_path(source_key)
        dest_path = self._build_object_path(dest_key)

        if fileio.exists(source_path):
            if not io_utils.is_remote(dest_path):
                parent_dir = str(Path(dest_path).parent)
                os.makedirs(parent_dir, exist_ok=True)
            fileio.rename(source_path, dest_path, overwrite=True)

    def list_keys(self, prefix: Tuple[str, ...] = ()) -> List[Tuple[str, ...]]:
        """List the keys of all objects identified by a partial key.

        Args:
            prefix: partial object key identifier.

        Returns:
            List of keys identifying all objects present in the store that
            match the input partial key.
        """
        key_list = []
        list_path = self._build_object_path(prefix, is_prefix=True)
        root_path = self._build_object_path(tuple(), is_prefix=True)
        for root, dirs, files in fileio.walk(list_path):
            for file_ in files:
                filepath = os.path.relpath(
                    os.path.join(str(root), str(file_)), root_path
                )

                if self.filepath_prefix and not filepath.startswith(
                    self.filepath_prefix
                ):
                    continue
                elif self.filepath_suffix and not filepath.endswith(
                    self.filepath_suffix
                ):
                    continue
                key = self._convert_filepath_to_key(filepath)
                if key and not self.is_ignored_key(key):
                    key_list.append(key)
        return key_list

    def remove_key(self, key: Tuple[str, ...]) -> bool:
        """Delete an object from the store.

        Args:
            key: object key identifier.

        Returns:
            True if the object existed in the store and was removed, otherwise
            False.
        """
        filepath: str = self._build_object_path(key)

        if fileio.exists(filepath):
            fileio.remove(filepath)
            if not io_utils.is_remote(filepath):
                parent_dir = str(Path(filepath).parent)
                self.rrmdir(self.root_path, str(parent_dir))
            return True
        return False

    def _has_key(self, key: Tuple[str, ...]) -> bool:
        """Check if an object is present in the store.

        Args:
            key: object key identifier.

        Returns:
            True if the object is present in the store, otherwise False.
        """
        filepath: str = self._build_object_path(key)
        result = fileio.exists(filepath)
        return result

    def get_url_for_key(
        self, key: Tuple[str, ...], protocol: Optional[str] = None
    ) -> str:
        """Get the URL of an object in the store.

        Args:
            key: object key identifier.
            protocol: optional protocol to use instead of the store protocol.

        Returns:
            The URL of the object in the store.
        """
        filepath = self._build_object_path(key)
        if not protocol and not io_utils.is_remote(filepath):
            protocol = "file:"
        if protocol:
            filepath = filepath.replace(self.proto, f"{protocol}//", 1)

        return filepath

    def get_public_url_for_key(
        self, key: str, protocol: Optional[str] = None
    ) -> str:
        """Get the public URL of an object in the store.

        Args:
            key: object key identifier.
            protocol: optional protocol to use instead of the store protocol.

        Returns:
            The public URL where the object can be accessed.

        Raises:
            StoreBackendError: if a `base_public_path` attribute was not
                configured for the store.
        """
        if not self.base_public_path:
            raise StoreBackendError(
                f"Error: No base_public_path was configured! A public URL was "
                f"requested but `base_public_path` was not configured for the "
                f"{self.__class__.__name__}"
            )
        filepath = self._convert_key_to_filepath(key)
        public_url = self.base_public_path + filepath.replace(self.proto, "")
        return cast(str, public_url)

    @staticmethod
    def rrmdir(start_path: str, end_path: str) -> None:
        """Recursively removes empty dirs between start_path and end_path inclusive.

        Args:
            start_path: Directory to use as a starting point.
            end_path: Directory to use as a destination point.
        """
        while not os.listdir(end_path) and start_path != end_path:
            os.rmdir(end_path)
            end_path = os.path.dirname(end_path)

    @property
    def config(self) -> Dict[str, Any]:
        """Get the store configuration.

        Returns:
            The store configuration.
        """
        return self._config
