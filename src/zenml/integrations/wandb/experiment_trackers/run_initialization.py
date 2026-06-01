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
"""Helpers for constructing Wandb run initialization arguments."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import NAMESPACE_URL, uuid5

from zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor import (
    WandbExperimentTrackerConfig,
    WandbExperimentTrackerSettings,
)
from zenml.logger import get_logger
from zenml.utils import dashboard_utils

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo


logger = get_logger(__name__)

DEFAULT_WANDB_SETTINGS: Dict[str, Any] = {
    "console": "off",
    "silent": True,
}


def sanitize_tag(tag: str) -> str:
    """Sanitize a tag to be a valid Wandb tag.

    Args:
        tag: The tag to sanitize.

    Returns:
        The sanitized tag.
    """
    return tag[:64]


def build_wandb_initialization(
    *,
    config: WandbExperimentTrackerConfig,
    settings: WandbExperimentTrackerSettings,
    info: "StepRunInfo",
) -> Dict[str, Any]:
    """Build Wandb initialization arguments for a ZenML step run.

    Args:
        config: The Wandb experiment tracker configuration.
        settings: Runtime settings for the step.
        info: Information about the ZenML step run.

    Returns:
        Wandb initialization arguments.
    """
    init_kwargs = dict(settings.init_kwargs)
    init_kwargs.update(
        {
            "entity": config.entity,
            "project": config.project_name,
            "name": _get_run_name(settings=settings, info=info),
            "tags": _get_tags(settings=settings, info=info),
            "settings": {**DEFAULT_WANDB_SETTINGS, **settings.settings},
        }
    )

    run_id = _get_run_id(settings=settings, info=info)
    if run_id:
        init_kwargs["id"] = run_id

    resume = settings.resume or ("allow" if run_id else None)
    if resume:
        init_kwargs["resume"] = resume

    if group := _get_group(settings=settings, info=info):
        init_kwargs["group"] = group

    if settings.job_type:
        init_kwargs["job_type"] = settings.job_type

    run_config = _get_run_config(settings=settings, info=info)
    if run_config:
        init_kwargs["config"] = run_config

    return init_kwargs


def _get_run_name(
    *, settings: WandbExperimentTrackerSettings, info: "StepRunInfo"
) -> str:
    """Get the Wandb display name for a ZenML step run."""
    if settings.run_name:
        return settings.run_name

    run_name = f"{info.run_name}_{info.pipeline_step_name}"
    if settings.run_id_strategy == "new_on_retry":
        return f"{run_name}_v{info.step_run.version}"

    return run_name


def _get_run_id(
    *, settings: WandbExperimentTrackerSettings, info: "StepRunInfo"
) -> Optional[str]:
    """Get the Wandb run ID for a ZenML step run."""
    if settings.run_id:
        return settings.run_id

    if settings.run_id_strategy == "new_on_retry":
        return uuid5(
            NAMESPACE_URL,
            f"zenml:wandb:step-run:{info.step_run_id}",
        ).hex

    if settings.run_id_strategy == "reuse_on_retry":
        return uuid5(
            NAMESPACE_URL,
            "zenml:wandb:pipeline-step:"
            f"{info.run_id}:{info.pipeline_step_name}",
        ).hex

    return None


def _get_group(
    *, settings: WandbExperimentTrackerSettings, info: "StepRunInfo"
) -> Optional[str]:
    """Get the Wandb group for a ZenML step run."""
    if settings.group:
        return settings.group

    if settings.enable_zenml_metadata:
        return info.run_name

    return None


def _get_tags(
    *, settings: WandbExperimentTrackerSettings, info: "StepRunInfo"
) -> List[str]:
    """Get Wandb tags for a ZenML step run."""
    tags = list(settings.tags)

    if settings.enable_zenml_metadata:
        tags.extend(["zenml", info.pipeline.name, info.run_name])

    return _deduplicate_tags(tags)


def _deduplicate_tags(tags: List[str]) -> List[str]:
    """Deduplicate tags after applying Wandb length limits."""
    deduplicated_tags: List[str] = []
    for tag in tags:
        sanitized_tag = sanitize_tag(tag)
        if sanitized_tag not in deduplicated_tags:
            deduplicated_tags.append(sanitized_tag)

    return deduplicated_tags


def _get_run_config(
    *, settings: WandbExperimentTrackerSettings, info: "StepRunInfo"
) -> Dict[str, Any]:
    """Get the Wandb run config for a ZenML step run."""
    run_config = dict(settings.run_config)

    if not settings.enable_zenml_metadata:
        return run_config

    run_config.update(
        {
            "zenml_pipeline_name": info.pipeline.name,
            "zenml_pipeline_run_id": str(info.run_id),
            "zenml_pipeline_run_name": info.run_name,
            "zenml_step_name": info.pipeline_step_name,
            "zenml_latest_step_run_id": str(info.step_run_id),
            "zenml_latest_step_run_version": info.step_run.version,
        }
    )

    if settings.enable_zenml_dashboard_links:
        run_config.update(_get_dashboard_links(info=info))

    return run_config


def _get_dashboard_links(info: "StepRunInfo") -> Dict[str, str]:
    """Get dashboard links for a ZenML step run if they are available."""
    dashboard_links: Dict[str, str] = {}

    try:
        from zenml.client import Client

        run = Client().zen_store.get_run(info.run_id)
        if run_url := dashboard_utils.get_run_url(run):
            dashboard_links["zenml_pipeline_run_url"] = run_url
    except Exception as e:
        logger.debug("Failed to derive ZenML dashboard links: %s", e)

    return dashboard_links
