#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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

import inspect
import os
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, cast

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


class TrackioExperimentTracker(BaseExperimentTracker):
    """Track experiments using Trackio."""

    @property
    def config(self) -> TrackioExperimentTrackerConfig:
        """Returns the Trackio config."""
        return cast(
            TrackioExperimentTrackerConfig,
            self._config,
        )

    @property
    def settings_class(
        self,
    ) -> Type[TrackioExperimentTrackerSettings]:
        """Settings class for Trackio."""
        return TrackioExperimentTrackerSettings

    def prepare_step_run(
        self,
        info: "StepRunInfo",
    ) -> None:
        """Configure a Trackio run.

        Args:
            info: Information about the step run.
        """
        if self.config.hf_token:
            previous_token: Optional[str] = os.environ.get(HF_TOKEN_ENV_VAR)

            setattr(
                info,
                "_trackio_previous_hf_token",
                previous_token,
            )

            os.environ[HF_TOKEN_ENV_VAR] = self.config.hf_token

        settings = cast(
            TrackioExperimentTrackerSettings,
            self.get_settings(info),
        )

        trackio_run_name = (
            settings.run_name or f"{info.run_name}_{info.pipeline_step_name}"
        )

        self._initialize_trackio(
            info=info,
            run_name=trackio_run_name,
        )

        tags = settings.tags

        if tags:
            try:
                trackio.log(
                    {
                        "zenml_tags": tags,
                    }
                )

            except Exception as e:
                logger.warning(
                    "Failed to log Trackio tags: %s",
                    e,
                )

    def get_step_run_metadata(
        self,
        info: "StepRunInfo",
    ) -> Dict[str, "MetadataType"]:
        """Get metadata after a step ran.

        Args:
            info: Information about the step run.

        Returns:
            Metadata containing the Trackio run name and optional run URL.
        """
        run_url: Optional[str] = None
        run_name: Optional[str] = None

        current_trackio_run = getattr(
            trackio,
            "run",
            None,
        )

        if current_trackio_run:
            run_name = getattr(
                current_trackio_run,
                "name",
                None,
            )

        if self.config.space_id:
            run_url = f"https://huggingface.co/spaces/{self.config.space_id}"
        elif self.config.server_url:
            run_url = self.config.server_url

        default_run_name = f"{info.run_name}_{info.pipeline_step_name}"

        settings = cast(
            TrackioExperimentTrackerSettings,
            self.get_settings(info),
        )

        run_name = run_name or settings.run_name or default_run_name

        metadata: Dict[str, "MetadataType"] = {
            "trackio_run_name": run_name,
        }

        if run_url:
            metadata[METADATA_EXPERIMENT_TRACKER_URL] = Uri(run_url)

        return metadata

    def cleanup_step_run(
        self,
        info: "StepRunInfo",
        step_failed: bool,
    ) -> None:
        """Finalize the Trackio run.

        Args:
            info: Information about the step run.
            step_failed: Whether the step failed.
        """
        settings = cast(
            TrackioExperimentTrackerSettings,
            self.get_settings(info),
        )

        try:
            if settings.auto_sync:
                logger.info("Syncing Trackio run.")

                sync_kwargs: Dict[str, Any] = {
                    "project": self.config.project_name,
                }

                # Publish to Hugging Face Space
                if self.config.space_id and settings.publish_to_space:
                    sync_kwargs["space_id"] = self.config.space_id

                # Publish to Hugging Face Dataset
                if self.config.dataset_id and settings.publish_to_dataset:
                    sync_kwargs["dataset_id"] = self.config.dataset_id

                # Optional bucket storage
                if self.config.bucket_id:
                    sync_kwargs["bucket_id"] = self.config.bucket_id

                trackio_any = cast(Any, trackio)

                valid_params = inspect.signature(trackio_any.sync).parameters

                logger.debug(
                    "valid sync params: %s",
                    valid_params.keys(),
                )
                filtered_kwargs: Dict[str, Any] = {
                    key: value
                    for key, value in sync_kwargs.items()
                    if key in valid_params and value is not None
                }

                logger.debug("Trackio sync kwargs: %s", filtered_kwargs)
                cast(Any, trackio).sync(**filtered_kwargs)

            if settings.auto_freeze and self.config.space_id:
                logger.info("Freezing Trackio dashboard.")

                freeze_kwargs: Dict[str, Any] = {
                    "space_id": self.config.space_id,
                    "project": self.config.project_name,
                }

                if self.config.bucket_id:
                    freeze_kwargs["bucket_id"] = self.config.bucket_id

                valid_params = inspect.signature(
                    cast(Any, trackio).freeze
                ).parameters
                filtered_kwargs = {
                    key: value
                    for key, value in freeze_kwargs.items()
                    if key in valid_params and value is not None
                }

                logger.debug("Trackio freeze kwargs: %s", filtered_kwargs)
                cast(Any, trackio).freeze(**filtered_kwargs)

        except Exception as e:
            logger.warning(
                "Failed to finalize Trackio sync/freeze: %s",
                e,
            )

        finally:
            cast(Any, trackio.finish)()

            if self.config.hf_token:
                previous_token: Optional[str] = getattr(
                    info,
                    "_trackio_previous_hf_token",
                    None,
                )

                if previous_token is not None:
                    os.environ[HF_TOKEN_ENV_VAR] = previous_token
                else:
                    os.environ.pop(
                        HF_TOKEN_ENV_VAR,
                        None,
                    )

    def _initialize_trackio(
        self,
        info: "StepRunInfo",
        run_name: str,
    ) -> None:
        """Initialize a Trackio run.

        Args:
            info: Information about the step run.
            run_name: Name to assign to the Trackio run.
        """
        logger.debug(
            "Initializing Trackio with project=%s, run_name=%s.",
            self.config.project_name,
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

        init_kwargs: Dict[str, Any] = {
            "project": self.config.project_name,
            "name": run_name,
            "config": config,
            "resume": settings.resume,
            "auto_log_gpu": settings.log_gpu_metrics,
        }

        if self.config.server_url:
            init_kwargs["server_url"] = self.config.server_url

        if self.config.space_id:
            init_kwargs["space_id"] = self.config.space_id

        if self.config.dataset_id:
            init_kwargs["dataset_id"] = self.config.dataset_id

        if self.config.bucket_id:
            init_kwargs["bucket_id"] = self.config.bucket_id

        valid_params = inspect.signature(trackio.init).parameters

        filtered_kwargs: Dict[str, Any] = {
            key: value
            for key, value in init_kwargs.items()
            if key in valid_params and value is not None
        }

        logger.debug(
            "Trackio init kwargs: %s",
            filtered_kwargs,
        )

        cast(Any, trackio.init)(**filtered_kwargs)

        logger.info("Trackio run initialized successfully.")
