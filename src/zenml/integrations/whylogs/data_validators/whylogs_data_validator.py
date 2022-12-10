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
"""Implementation of the whylogs data validator."""

import datetime
import os
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Sequence, Type, cast

import pandas as pd
import whylogs as why  # type: ignore
from whylogs.api.writer.whylabs import WhyLabsWriter  # type: ignore
from whylogs.core import DatasetProfileView  # type: ignore

from zenml.config.base_settings import BaseSettings
from zenml.data_validators import BaseDataValidator, BaseDataValidatorFlavor
from zenml.environment import Environment
from zenml.integrations.whylogs.constants import (
    WHYLABS_DATASET_ID_ENV,
    WHYLABS_LOGGING_ENABLED_ENV,
)
from zenml.integrations.whylogs.flavors.whylogs_data_validator_flavor import (
    WhylogsDataValidatorConfig,
    WhylogsDataValidatorFlavor,
    WhylogsDataValidatorSettings,
)
from zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema import (
    WhylabsSecretSchema,
)
from zenml.logger import get_logger
from zenml.stack.authentication_mixin import AuthenticationMixin
from zenml.steps import STEP_ENVIRONMENT_NAME, StepEnvironment

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo

logger = get_logger(__name__)


class WhylogsDataValidator(BaseDataValidator, AuthenticationMixin):
    """Whylogs data validator stack component.

    Attributes:
        authentication_secret: Optional ZenML secret with Whylabs credentials.
            If configured, all the data profiles returned by all pipeline steps
            will automatically be uploaded to Whylabs in addition to being
            stored in the ZenML Artifact Store.
    """

    NAME: ClassVar[str] = "whylogs"
    FLAVOR: ClassVar[Type[BaseDataValidatorFlavor]] = WhylogsDataValidatorFlavor

    @property
    def config(self) -> WhylogsDataValidatorConfig:
        """Returns the `WhylogsDataValidatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(WhylogsDataValidatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Whylogs data validator.

        Returns:
            The settings class.
        """
        return WhylogsDataValidatorSettings

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Configures Whylabs logging.

        Args:
            info: Info about the step that will be executed.
        """
        settings = cast(WhylogsDataValidatorSettings, self.get_settings(info))
        if settings.enable_whylabs:
            os.environ[WHYLABS_LOGGING_ENABLED_ENV] = "true"
        if settings.dataset_id:
            os.environ[WHYLABS_DATASET_ID_ENV] = settings.dataset_id

    def cleanup_step_run(self, info: "StepRunInfo", step_failed: bool) -> None:
        """Resets Whylabs configuration.

        Args:
            info: Info about the step that was executed.
            step_failed: Whether the step failed.
        """
        settings = cast(WhylogsDataValidatorSettings, self.get_settings(info))
        if settings.enable_whylabs:
            del os.environ[WHYLABS_LOGGING_ENABLED_ENV]
        if settings.dataset_id:
            del os.environ[WHYLABS_DATASET_ID_ENV]

    def data_profiling(
        self,
        dataset: pd.DataFrame,
        comparison_dataset: Optional[pd.DataFrame] = None,
        profile_list: Optional[Sequence[str]] = None,
        dataset_timestamp: Optional[datetime.datetime] = None,
        **kwargs: Any,
    ) -> DatasetProfileView:
        """Analyze a dataset and generate a data profile with whylogs.

        Args:
            dataset: Target dataset to be profiled.
            comparison_dataset: Optional dataset to be used for data profiles
                that require a baseline for comparison (e.g data drift profiles).
            profile_list: Optional list identifying the categories of whylogs
                data profiles to be generated (unused).
            dataset_timestamp: timestamp to associate with the generated
                dataset profile (Optional). The current time is used if not
                supplied.
            **kwargs: Extra keyword arguments (unused).

        Returns:
            A whylogs profile view object.
        """
        results = why.log(pandas=dataset)
        profile = results.profile()
        dataset_timestamp = dataset_timestamp or datetime.datetime.utcnow()
        profile.set_dataset_timestamp(dataset_timestamp=dataset_timestamp)
        return profile.view()

    def upload_profile_view(
        self,
        profile_view: DatasetProfileView,
        dataset_id: Optional[str] = None,
    ) -> None:
        """Upload a whylogs data profile view to Whylabs, if configured to do so.

        Args:
            profile_view: Whylogs profile view to upload.
            dataset_id: Optional dataset identifier to use for the uploaded
                data profile. If omitted, a dataset identifier will be retrieved
                using other means, in order:
                    * the default dataset identifier configured in the Data
                    Validator secret
                    * a dataset ID will be generated automatically based on the
                    current pipeline/step information.

        Raises:
            ValueError: If the dataset ID was not provided and could not be
                retrieved or inferred from other sources.
        """
        secret = self.get_authentication_secret(
            expected_schema_type=WhylabsSecretSchema
        )
        if not secret:
            return

        dataset_id = dataset_id or secret.whylabs_default_dataset_id

        if not dataset_id:
            # use the current pipeline name and the step name to generate a
            # unique dataset name
            try:
                # get pipeline name and step name
                step_env = cast(
                    StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME]
                )
                dataset_id = f"{step_env.pipeline_name}_{step_env.step_name}"
            except KeyError:
                raise ValueError(
                    "A dataset ID was not specified and could not be "
                    "generated from the current pipeline and step name."
                )

        # Instantiate WhyLabs Writer
        writer = WhyLabsWriter(
            org_id=secret.whylabs_default_org_id,
            api_key=secret.whylabs_api_key,
            dataset_id=dataset_id,
        )

        # pass a profile view to the writer's write method
        writer.write(profile=profile_view)
