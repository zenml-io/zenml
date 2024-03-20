#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Utility functions for the orchestrator."""

import random
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional
from uuid import UUID

from zenml.client import Client
from zenml.config.global_config import (
    GlobalConfiguration,
)
from zenml.constants import (
    ENV_ZENML_ACTIVE_STACK_ID,
    ENV_ZENML_ACTIVE_WORKSPACE_ID,
    ENV_ZENML_STORE_PREFIX,
    PIPELINE_API_TOKEN_EXPIRES_MINUTES,
)
from zenml.enums import StoreType

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse


def get_orchestrator_run_name(pipeline_name: str) -> str:
    """Gets an orchestrator run name.

    This run name is not the same as the ZenML run name but can instead be
    used to display in the orchestrator UI.

    Args:
        pipeline_name: Name of the pipeline that will run.

    Returns:
        The orchestrator run name.
    """
    return f"{pipeline_name}_{random.Random().getrandbits(128):032x}"


def is_setting_enabled(
    is_enabled_on_step: Optional[bool],
    is_enabled_on_pipeline: Optional[bool],
) -> bool:
    """Checks if a certain setting is enabled within a step run.

    This is the case if:
    - the setting is explicitly enabled for the step, or
    - the setting is neither explicitly disabled for the step nor the pipeline.

    Args:
        is_enabled_on_step: The setting of the step.
        is_enabled_on_pipeline: The setting of the pipeline.

    Returns:
        True if the setting is enabled within the step run, False otherwise.
    """
    if is_enabled_on_step is not None:
        return is_enabled_on_step
    if is_enabled_on_pipeline is not None:
        return is_enabled_on_pipeline
    return True


def get_config_environment_vars(
    deployment: Optional["PipelineDeploymentResponse"] = None,
) -> Dict[str, str]:
    """Gets environment variables to set for mirroring the active config.

    If a pipeline deployment is given, the environment variables will be set to
    include a newly generated API token valid for the duration of the pipeline
    run instead of the API token from the global config.

    Args:
        deployment: Optional deployment to use for the environment variables.

    Returns:
        Environment variable dict.
    """
    from zenml.zen_stores.rest_zen_store import RestZenStore

    global_config = GlobalConfiguration()
    environment_vars = global_config.get_config_environment_vars()

    if deployment and global_config.store_configuration.type == StoreType.REST:
        # When connected to a ZenML server, if a pipeline deployment is
        # supplied, we need to fetch an API token that will be valid for the
        # duration of the pipeline run.
        assert isinstance(global_config.zen_store, RestZenStore)
        pipeline_id: Optional[UUID] = None
        if deployment.pipeline:
            pipeline_id = deployment.pipeline.id
        schedule_id: Optional[UUID] = None
        expires_minutes: Optional[int] = PIPELINE_API_TOKEN_EXPIRES_MINUTES
        if deployment.schedule:
            schedule_id = deployment.schedule.id
            # If a schedule is given, this is a long running pipeline that
            # should not have an API token that expires.
            expires_minutes = None
        api_token = global_config.zen_store.get_api_token(
            pipeline_id=pipeline_id,
            schedule_id=schedule_id,
            expires_minutes=expires_minutes,
        )
        environment_vars[ENV_ZENML_STORE_PREFIX + "API_TOKEN"] = api_token

    # Make sure to use the correct active stack/workspace which might come
    # from a .zen repository and not the global config
    environment_vars[ENV_ZENML_ACTIVE_STACK_ID] = str(
        Client().active_stack_model.id
    )
    environment_vars[ENV_ZENML_ACTIVE_WORKSPACE_ID] = str(
        Client().active_workspace.id
    )

    return environment_vars


def get_run_name(run_name_template: str) -> str:
    """Fill out the run name template to get a complete run name.

    Args:
        run_name_template: The run name template to fill out.

    Raises:
        ValueError: If the run name is empty.

    Returns:
        The run name derived from the template.
    """
    date = datetime.utcnow().strftime("%Y_%m_%d")
    time = datetime.utcnow().strftime("%H_%M_%S_%f")

    run_name = run_name_template.format(date=date, time=time)

    if run_name == "":
        raise ValueError("Empty run names are not allowed.")

    return run_name
