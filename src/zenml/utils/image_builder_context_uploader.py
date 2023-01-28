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
"""Implementation of Docker image build context uploader."""

import hashlib
import tempfile
from typing import TYPE_CHECKING

from zenml.io import fileio
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.image_builders import BuildContext


logger = get_logger(__name__)


class ImageBuilderContextUploader:
    """Generate and uploads Docker image build context to a remote location."""

    @staticmethod
    def upload_build_context(
        build_context: "BuildContext",
        parent_path: str,
    ) -> str:
        """Uploads a Docker image build context to a remote location.

        Args:
            build_context: The build context to upload.
            parent_path: The parent path to upload to.

        Returns:
            The path to the uploaded build context.
        """
        hash_ = hashlib.sha1()
        with tempfile.NamedTemporaryFile(mode="w+b") as f:
            build_context.write_archive(f, gzip=True)

            while True:
                data = f.read(64 * 1024)
                if not data:
                    break
                hash_.update(data)

            filename = f"{hash_.hexdigest()}.tar.gz"
            filepath = f"{parent_path}/{filename}"
            if not fileio.exists(filepath):
                logger.info("Uploading build context to `%s`.", filepath)
                fileio.copy(f.name, filepath)
            else:
                logger.info("Build context already exists, not uploading.")

        return filepath
