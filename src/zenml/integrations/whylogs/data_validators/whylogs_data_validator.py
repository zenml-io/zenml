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
import pandas as pd
import whylogs as why  # type: ignore

from typing import Any, ClassVar, Optional, Sequence, cast


from zenml.data_validators import BaseDataValidator
from zenml.environment import Environment
from zenml.integrations.whylogs import WHYLOGS_DATA_VALIDATOR_FLAVOR
from zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema import (
    WhylabsSecretSchema,
)
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.steps import STEP_ENVIRONMENT_NAME, StepEnvironment

from whylogs.api.writer.whylabs import WhyLabsWriter  # type: ignore
from whylogs.core import DatasetProfileView  # type: ignore

logger = get_logger(__name__)


class WhylogsDataValidator(BaseDataValidator):
    """Whylogs data validator stack component.

    Attributes:
        whylabs_secret: Optional ZenML secret with Whylabs credentials. If
            configured, all the data profiles returned by all pipeline steps
            will automatically be uploaded to Whylabs in addition to being
            stored in the ZenML Artifact Store.
    """

    whylabs_secret: Optional[str] = None

    # Class Configuration
    FLAVOR: ClassVar[str] = WHYLOGS_DATA_VALIDATOR_FLAVOR
    NAME: ClassVar[str] = "whylogs"

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

    def _get_whylabs_secret(self) -> Optional[WhylabsSecretSchema]:
        """Load the Whylabs secret from the active secrets manager.

        Returns:
            The Whylabs secret, if one was configured, otherwise None.

        Raises:
            RuntimeError: if the configured secret cannot be loaded.
        """
        # if a ZenML secret was configured in the model deployer,
        # create a Kubernetes secret as a means to pass this information
        # to the Seldon Core deployment
        if not self.whylabs_secret:
            return None

        secret_manager = Repository(  # type: ignore [call-arg]
            skip_repository_check=True
        ).active_stack.secrets_manager

        if not secret_manager:
            raise RuntimeError(
                f"The active stack doesn't have a secret manager component. "
                f"The Whylabs secret specified in the whylogs Data Validator "
                f"configuration cannot be fetched: {self.whylabs_secret}."
            )

        try:
            whylabs_secret = secret_manager.get_secret(self.whylabs_secret)
        except KeyError:
            raise RuntimeError(
                f"The Whylabs secret '{self.whylabs_secret}' specified in the "
                f"whylogs Data Validateor configuration was not found "
                f"in the active secrets manager."
            )

        if not isinstance(whylabs_secret, WhylabsSecretSchema):
            raise RuntimeError(
                f"The Whylabs secret '{self.whylabs_secret}' loaded from the "
                f"active secrets manager is not of type {WhylabsSecretSchema}. "
                f"Please ensure that you use the `{WhylabsSecretSchema.TYPE}` "
                f"schema type when you configure the Whylabs secret."
            )

        return whylabs_secret

    def upload_profile_view(
        self, profile_view: DatasetProfileView, dataset_id: Optional[str] = None
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
        secret = self._get_whylabs_secret()
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
