#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""LangSmith experiment tracker flavor."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Type,
)

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTrackerConfig,
    BaseExperimentTrackerFlavor,
)
from zenml.integrations.langsmith import LANGSMITH_EXPERIMENT_TRACKER_FLAVOR
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.langsmith.experiment_trackers import (
        LangSmithExperimentTracker,
    )


class LangSmithExperimentTrackerSettings(BaseSettings):
    """Settings for the LangSmith experiment tracker.

    Attributes:
        run_name: The LangSmith experiment name.
        tags: Tags for the LangSmith experiment.
        settings: Settings for the LangSmith experiment.
    """
    tags: List[str] = []
    settings: Dict[str, Any] = {}


class LangSmithExperimentTrackerConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseExperimentTrackerConfig, LangSmithExperimentTrackerSettings
):
    """Config for the LangSmith experiment tracker.

    Attributes:
        workspace: Name of an existing LangSmith workspace.
        project_name: Name of an existing LangSmith project to log to.
        api_key: API key that should be authorized to log to the configured LangSmith
            workspace and project.
    """

    api_key: str = SecretField()
    workspace: Optional[str] = None
    project_name: Optional[str] = None


class LangSmithExperimentTrackerFlavor(BaseExperimentTrackerFlavor):
    """Flavor for the LangSmith experiment tracker."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return LANGSMITH_EXPERIMENT_TRACKER_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/experiment_tracker/langsmith.png"

    @property
    def config_class(self) -> Type[LangSmithExperimentTrackerConfig]:
        """Returns `LangSmithExperimentTrackerConfig` config class.

        Returns:
                The config class.
        """
        return LangSmithExperimentTrackerConfig

    @property
    def implementation_class(self) -> Type["LangSmithExperimentTracker"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.langsmith.experiment_trackers import (
            LangSmithExperimentTracker,
        )

        return LangSmithExperimentTracker
