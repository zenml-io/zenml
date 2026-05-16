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
"""Implementation for the trackio experiment tracker."""
import os
from typing import TYPE_CHECKING, Dict, List, Optional, Type, cast

import trackio

from zenml.constants import METADATA_EXPERIMENT_TRACKER_URL
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.trackio.flavors.trackio_experiment_tracker_flavor import (
    TrackioExperimentTrackerConfig,
    TrackioExperimentTrackerSettings,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import Uri

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.metadata.metadata_types import MetadataType


logger = get_logger(__name__)

HF_TOKEN_ENV_VAR = "HF_TOKEN"


def sanitize_tag(tag: str) -> str:
    """Sanitize a tag to be a valid Trackio tag.

    Args:
        tag: The tag to sanitize.

    Returns:
        The sanitized tag.
    """
    return tag.replace("/", "-")[:64]


class TrackioExperimentTracker(BaseExperimentTracker):
    """Track experiments using Trackio."""

    @property
    def config(self) -> TrackioExperimentTrackerConfig:
        """Returns the `TrackioExperimentTrackerConfig` config.

        Returns:
            The configuration.
        """
        return cast(TrackioExperimentTrackerConfig, self._config)

    @property
    def settings_class(self) -> Type[TrackioExperimentTrackerSettings]:
        """Settings class for the Trackio experiment tracker.

        Returns:
            The settings class.
        """
        return TrackioExperimentTrackerSettings

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Configures a Trackio run.

        Args:
            info: Info about the step that will be executed.
        """
        if self.config.hf_token:
            os.environ[HF_TOKEN_ENV_VAR] = self.config.hf_token

        settings = cast(
            TrackioExperimentTrackerSettings,
            self.get_settings(info),
        )

        tags = settings.tags + [
            sanitize_tag(info.run_name),
            sanitize_tag(info.pipeline.name),
        ]

        trackio_run_name = (
            settings.run_name
            or f"{info.run_name}_{info.pipeline_step_name}"
        )

        self._initialize_trackio(
            info=info,
            run_name=trackio_run_name,
            tags=tags,
        )

    def get_step_run_metadata(
        self,
        info: "StepRunInfo",
    ) -> Dict[str, "MetadataType"]:
        """Get component- and step-specific metadata after a step ran.

        Args:
            info: Info about the step that was executed.

        Returns:
            A dictionary of metadata.
        """
        run_url: Optional[str] = None
        run_name: Optional[str] = None

        current_trackio_run = getattr(trackio, "run", None)

        if current_trackio_run:
            run_url = getattr(current_trackio_run, "url", None)
            run_name = getattr(current_trackio_run, "name", None)

        default_run_name = (
            f"{info.run_name}_{info.pipeline_step_name}"
        )

        settings = cast(
            TrackioExperimentTrackerSettings,
            self.get_settings(info),
        )

        run_name = (
            run_name
            or settings.run_name
            or default_run_name
        )

        metadata: Dict[str, "MetadataType"] = {
            "trackio_run_name": run_name,
        }

        if run_url:
            metadata[
                METADATA_EXPERIMENT_TRACKER_URL
            ] = Uri(run_url)

        return metadata

    def cleanup_step_run(
        self,
        info: "StepRunInfo",
        step_failed: bool,
    ) -> None:
        """Stops the Trackio run.

        Args:
            info: Info about the step that was executed.
            step_failed: Whether the step failed or not.
        """
        settings = cast(
            TrackioExperimentTrackerSettings,
            self.get_settings(info),
        )

        try:
            if settings.auto_sync:
                logger.info("Syncing Trackio run.")
                trackio.sync()

            if settings.auto_freeze:
                logger.info("Freezing Trackio dashboard.")
                trackio.freeze()

        except Exception as e:
            logger.warning(
                "Failed to finalize Trackio sync/freeze: %s",
                e,
            )

        finally:
            trackio.finish()

            if self.config.hf_token:
                os.environ.pop(HF_TOKEN_ENV_VAR, None)

    def _initialize_trackio(
        self,
        info: "StepRunInfo",
        run_name: str,
        tags: List[str],
    ) -> None:
        """Initializes a Trackio run.

        Args:
            info: Step run information.
            run_name: Name of the Trackio run to create.
            tags: Tags to attach to the Trackio run.
        """
        logger.info(
            "Initializing Trackio with project=%s, "
            "backend=%s, run_name=%s.",
            self.config.project_name,
            self.config.backend,
            run_name,
        )

        settings = cast(
            TrackioExperimentTrackerSettings,
            self.get_settings(info),
        )

        config = {
            "zenml": {
                "pipeline_name": info.pipeline.name,
                "step_name": info.pipeline_step_name,
                "run_name": info.run_name,
            }
        }

        init_kwargs = {
            "project": self.config.project_name,
            "name": run_name,
            "tags": tags,
            "config": config,
            "dir": self.config.local_dir,
            "resume": settings.resume,
        }

        if self.config.tracking_uri:
            init_kwargs["tracking_uri"] = (
                self.config.tracking_uri
            )

        if self.config.workspace:
            init_kwargs["workspace"] = (
                self.config.workspace
            )

        if self.config.backend == "static":
            init_kwargs["sdk"] = "static"

        if self.config.hf_space:
            init_kwargs["space"] = self.config.hf_space

        trackio.init(**init_kwargs)

        logger.info(
            "Trackio run initialized successfully."
        )