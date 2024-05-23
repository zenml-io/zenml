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
"""Neptune experiment tracker flavor."""

__all__ = [
    "NeptuneExperimentTrackerConfig",
    "NeptuneExperimentTrackerFlavor",
    "NeptuneExperimentTrackerSettings",
]

from typing import TYPE_CHECKING, Optional, Set, Type

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTrackerConfig,
    BaseExperimentTrackerFlavor,
)
from zenml.integrations.neptune import NEPTUNE_MODEL_EXPERIMENT_TRACKER_FLAVOR
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.neptune.experiment_trackers import (
        NeptuneExperimentTracker,
    )


class NeptuneExperimentTrackerConfig(BaseExperimentTrackerConfig):
    """Config for the Neptune experiment tracker.

    If attributes are left as None, the neptune.init_run() method
    will try to find the relevant values in the environment

    Attributes:
        project: name of the Neptune project you want to log the metadata to
        api_token: your Neptune API token
    """

    project: Optional[str] = None
    api_token: Optional[str] = SecretField(default=None)


class NeptuneExperimentTrackerSettings(BaseSettings):
    """Settings for the Neptune experiment tracker.

    Attributes:
        tags: Tags for the Neptune run.
    """

    tags: Set[str] = set()


class NeptuneExperimentTrackerFlavor(BaseExperimentTrackerFlavor):
    """Class for the `NeptuneExperimentTrackerFlavor`."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return NEPTUNE_MODEL_EXPERIMENT_TRACKER_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/experiment_tracker/neptune.png"

    @property
    def config_class(self) -> Type[NeptuneExperimentTrackerConfig]:
        """Returns `NeptuneExperimentTrackerConfig` config class.

        Returns:
                The config class.
        """
        return NeptuneExperimentTrackerConfig

    @property
    def implementation_class(self) -> Type["NeptuneExperimentTracker"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.neptune.experiment_trackers import (
            NeptuneExperimentTracker,
        )

        return NeptuneExperimentTracker
