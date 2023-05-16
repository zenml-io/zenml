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
#
# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Filesystem registry managing filesystem plugins."""

import re
from threading import Lock
from typing import TYPE_CHECKING, Dict, Type

from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.io.filesystem import BaseFilesystem, PathType


logger = get_logger(__name__)


class FileIORegistry:
    """Registry of pluggable filesystem implementations."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._filesystems: Dict["PathType", Type["BaseFilesystem"]] = {}
        self._registration_lock = Lock()

    def register(self, filesystem_cls: Type["BaseFilesystem"]) -> None:
        """Register a filesystem implementation.

        Args:
            filesystem_cls: Subclass of `zenml.io.filesystem.Filesystem`.
        """
        with self._registration_lock:
            for scheme in filesystem_cls.SUPPORTED_SCHEMES:
                current_preferred = self._filesystems.get(scheme)
                if current_preferred is not None:
                    logger.debug(
                        "Overwriting previously registered filesystem for "
                        "scheme `%s`. Old class: %s, new class: %s",
                        scheme,
                        current_preferred.__name__,
                        filesystem_cls.__name__,
                    )

                self._filesystems[scheme] = filesystem_cls

    def get_filesystem_for_scheme(
        self, scheme: "PathType"
    ) -> Type["BaseFilesystem"]:
        """Get filesystem plugin for given scheme string.

        Args:
            scheme: The scheme to get the filesystem for.

        Returns:
            The filesystem plugin for the given scheme.

        Raises:
            ValueError: If no filesystem plugin is registered for the given
                scheme.
        """
        if isinstance(scheme, bytes):
            scheme = scheme.decode("utf-8")
        if scheme not in self._filesystems:
            raise ValueError(
                f"No file systems were found for the scheme: "
                f"{scheme}. Please make sure that you are using "
                f"the right path and the all the necessary "
                f"integrations are properly installed."
            )
        return self._filesystems[scheme]

    def get_filesystem_for_path(
        self, path: "PathType"
    ) -> Type["BaseFilesystem"]:
        """Get filesystem plugin for given path.

        Args:
            path: The path to get the filesystem for.

        Returns:
            The filesystem plugin for the given path.

        Raises:
            ValueError: If no filesystem plugin is registered for the given
                path.
        """
        # Assume local path by default, but extract filesystem prefix if available.
        if isinstance(path, str):
            path_bytes = path.encode("utf-8")
        elif isinstance(path, bytes):
            path_bytes = path
        else:
            raise ValueError("Invalid path type: %r." % path)
        result = re.match(b"^([a-z0-9]+://)", path_bytes)
        if result:
            scheme = result.group(1).decode("utf-8")
        else:
            scheme = ""
        return self.get_filesystem_for_scheme(scheme)


# Default global instance of the filesystem registry.
default_filesystem_registry = FileIORegistry()
