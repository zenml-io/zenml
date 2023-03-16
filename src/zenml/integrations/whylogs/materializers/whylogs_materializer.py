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
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

logger = get_logger(__name__)

PROFILE_FILENAME = "profile.pb"


class WhylogsMaterializer(BaseMaterializer):
    """Materializer to read/write whylogs dataset profile views."""

    ASSOCIATED_TYPES = (DatasetProfileView,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA_ANALYSIS

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

        try:
            self._upload_to_whylabs(profile_view)
        except Exception as e:
            logger.error(
                "Failed to upload whylogs profile view to Whylabs: %s", e
            )

    def _upload_to_whylabs(self, profile_view: DatasetProfileView) -> None:
        """Uploads a whylogs dataset profile view to Whylabs.

        Args:
            profile_view: A whylogs dataset profile view object.
        """
        from zenml.environment import Environment
        from zenml.integrations.whylogs.data_validators import (
            WhylogsDataValidator,
        )
        from zenml.integrations.whylogs.flavors.whylogs_data_validator_flavor import (
            WhylogsDataValidatorSettings,
        )
        from zenml.steps import STEP_ENVIRONMENT_NAME, StepEnvironment

        try:
            data_validator = WhylogsDataValidator.get_active_data_validator()
        except TypeError:
            # no whylogs data validator is active
            return

        if not isinstance(data_validator, WhylogsDataValidator):
            # the active data validator is not a whylogs data validator
            return

        try:
            step_env = cast(
                StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME]
            )
        except KeyError:
            # we are not in a step environment
            return

        run_info = step_env.step_run_info
        settings = cast(
            WhylogsDataValidatorSettings, data_validator.get_settings(run_info)
        )

        if not settings.enable_whylabs:
            # whylabs is not enabled in the data validator
            return
        data_validator.upload_profile_view(
            profile_view, dataset_id=settings.dataset_id
        )
