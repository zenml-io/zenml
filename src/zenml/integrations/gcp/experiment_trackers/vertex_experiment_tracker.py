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
"""Implementation of the VertexAI experiment tracker for ZenML."""

import re
from typing import TYPE_CHECKING, Dict, Optional, Type, cast

from google.api_core import exceptions
from google.cloud import aiplatform
from google.cloud.aiplatform.compat.types import execution

from zenml.constants import METADATA_EXPERIMENT_TRACKER_URL
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.gcp.flavors.vertex_experiment_tracker_flavor import (
    VertexExperimentTrackerConfig,
    VertexExperimentTrackerSettings,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import Uri

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.metadata.metadata_types import MetadataType

logger = get_logger(__name__)


class VertexExperimentTracker(BaseExperimentTracker, GoogleCredentialsMixin):
    """Track experiments using VertexAI."""

    @property
    def config(self) -> VertexExperimentTrackerConfig:
        """Returns the `VertexExperimentTrackerConfig` config.

        Returns:
            The configuration.
        """
        return cast(VertexExperimentTrackerConfig, self._config)

    @property
    def settings_class(self) -> Type[VertexExperimentTrackerSettings]:
        """Returns the `BaseSettings` settings class.

        Returns:
            The settings class.
        """
        return VertexExperimentTrackerSettings

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Configures a VertexAI run.

        Args:
            info: Info about the step that will be executed.
        """
        self._initialize_vertex(info=info)

    def get_step_run_metadata(
        self, info: "StepRunInfo"
    ) -> Dict[str, "MetadataType"]:
        """Get component- and step-specific metadata after a step ran.

        Args:
            info: Info about the step that was executed.

        Returns:
            A dictionary of metadata.
        """
        run_name = self._get_run_name(info=info)
        run_url = self._get_run_url(info=info)
        return {
            METADATA_EXPERIMENT_TRACKER_URL: Uri(run_url),
            "vertex_run_name": run_name,
        }

    def _format_name(self, name: str) -> str:
        return re.sub(r"[^a-z0-9-]", "-", name.strip().lower())[:128].rstrip(
            "-"
        )

    def _get_experiment_name(self, info: "StepRunInfo") -> str:
        """Gets the experiment name.

        Args:
            info: Info about the
        """
        settings = cast(
            VertexExperimentTrackerSettings, self.get_settings(info)
        )
        name = settings.experiment or info.pipeline.name
        return self._format_name(name)

    def _get_run_name(self, info: "StepRunInfo") -> str:
        """Gets the run name.

        Args:
            info: Info about the step that will be executed.

        Returns:
            The run name.
        """
        return self._format_name(info.run_name)

    def _get_tensorboard_resource_name(self, experiment: str) -> Optional[str]:
        resource = aiplatform.Experiment(
            experiment
        ).get_backing_tensorboard_resource()
        resource_name = (
            str(resource.resource_name) if resource is not None
            else None
        )
        return resource_name

    def _initialize_vertex(self, info: "StepRunInfo") -> None:
        """Initializes a VertexAI run.

        Args:
            info: Info about the step that will be executed.
        """
        settings = cast(
            VertexExperimentTrackerSettings, self.get_settings(info)
        )
        experiment = self._get_experiment_name(info=info)
        run_name = self._get_run_name(info=info)
        credentials, project = self._get_authentication()
        logger.info(
            f"Initializing VertexAI with experiment name {experiment} "
            f"and run name {run_name}."
        )

        aiplatform.init(
            project=project,
            location=self.config.location,
            experiment=experiment,
            experiment_tensorboard=settings.experiment_tensorboard,
            staging_bucket=self.config.staging_bucket,
            credentials=credentials,
            encryption_spec_key_name=self.config.encryption_spec_key_name,
            network=self.config.network,
            api_endpoint=self.config.api_endpoint,
            api_key=self.config.api_key,
            api_transport=self.config.api_transport,
            request_metadata=self.config.request_metadata,
        )

        try:
            aiplatform.start_run(
                run=run_name,
                tensorboard=settings.experiment_tensorboard,
                resume=True,
            )
        except exceptions.NotFound:
            aiplatform.start_run(
                run=run_name,
                tensorboard=settings.experiment_tensorboard,
                resume=False,
            )

        logger.info(
            f"Tensorboard resource name: {self._get_tensorboard_resource_name(experiment=experiment)}"
        )

    def _get_run_url(self, info: "StepRunInfo") -> str:
        """Gets the run URL.

        Args:
            info: Info about the step that will be executed.

        Returns:
            The run URL.
        """
        settings = cast(
            VertexExperimentTrackerSettings, self.get_settings(info)
        )
        experiment = settings.experiment or info.pipeline.name
        run_name = self._get_run_name(info=info)
        run_url = (
            f"https://console.cloud.google.com/vertex-ai/experiments/locations/"
            f"{self.config.location}/experiments/{experiment}/runs/"
            f"{run_name}/charts?project={self.config.project}"
        )
        return run_url

    def cleanup_step_run(self, info: "StepRunInfo", step_failed: bool) -> None:
        """Stops the VertexAI run.

        Args:
            info: Info about the step that was executed.
            step_failed: Whether the step failed or not.
        """
        state = (
            execution.Execution.State.FAILED
            if step_failed
            else execution.Execution.State.COMPLETE
        )
        aiplatform.end_run(state=state)
