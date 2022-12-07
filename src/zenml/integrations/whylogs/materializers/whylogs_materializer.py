#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of the whylogs materializer."""

import os
import tempfile
from typing import Any, Type, cast

from whylogs.core import DatasetProfileView  # type: ignore

from zenml.enums import ArtifactType
from zenml.integrations.whylogs.constants import (
    WHYLABS_DATASET_ID_ENV,
    WHYLABS_LOGGING_ENABLED_ENV,
)
from zenml.integrations.whylogs.data_validators import WhylogsDataValidator
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

PROFILE_FILENAME = "profile.pb"


class WhylogsMaterializer(BaseMaterializer):
    """Materializer to read/write whylogs dataset profile views."""

    ASSOCIATED_TYPES = (DatasetProfileView,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.STATISTICS

    def load(self, data_type: Type[Any]) -> DatasetProfileView:
        """Reads and returns a whylogs dataset profile view.

        Args:
            data_type: The type of the data to read.

        Returns:
            A loaded whylogs dataset profile view object.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, PROFILE_FILENAME)

        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(str(temp_dir), PROFILE_FILENAME)

        # Copy from artifact store to temporary file
        fileio.copy(filepath, temp_file)
        profile_view = DatasetProfileView.read(temp_file)

        # Cleanup and return
        fileio.rmtree(temp_dir)

        return profile_view

    def save(self, profile_view: DatasetProfileView) -> None:
        """Writes a whylogs dataset profile view.

        Args:
            profile_view: A whylogs dataset profile view object.
        """
        super().save(profile_view)
        filepath = os.path.join(self.uri, PROFILE_FILENAME)

        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(str(temp_dir), PROFILE_FILENAME)

        profile_view.write(temp_file)

        # Copy it into artifact store
        fileio.copy(temp_file, filepath)
        fileio.rmtree(temp_dir)

        # Use the data validator to upload the profile view to Whylabs,
        # if configured to do so. This logic is only enabled if the pipeline
        # step was decorated with the `enable_whylabs` decorator
        whylabs_enabled = os.environ.get(WHYLABS_LOGGING_ENABLED_ENV)
        if not whylabs_enabled:
            return
        dataset_id = os.environ.get(WHYLABS_DATASET_ID_ENV)
        data_validator = cast(
            WhylogsDataValidator,
            WhylogsDataValidator.get_active_data_validator(),
        )
        data_validator.upload_profile_view(profile_view, dataset_id=dataset_id)
