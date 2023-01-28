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
import tempfile

from zenml.image_builders import BuildContext
from zenml.io import fileio
from zenml.utils.image_builder_context_uploader import (
    ImageBuilderContextUploader,
)


def _get_build_context() -> BuildContext:
    """Get a build context for testing.

    Returns:
        A build context.
    """
    return BuildContext(root=".", dockerignore_file=None)


def test_upload_build_context() -> None:
    """Test that the build context is uploaded correctly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        filepath = ImageBuilderContextUploader.upload_build_context(
            build_context=_get_build_context(), parent_path=tmp_dir
        )
        assert fileio.exists(filepath)
