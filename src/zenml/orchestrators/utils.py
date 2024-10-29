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

import os
import random
from typing import TYPE_CHECKING, Any, Dict, Optional, cast
from uuid import UUID

from zenml.client import Client
from zenml.config.global_config import (
    GlobalConfiguration,
)
from zenml.constants import (
    ENV_ZENML_ACTIVE_STACK_ID,
    ENV_ZENML_ACTIVE_WORKSPACE_ID,
    ENV_ZENML_SERVER,
    ENV_ZENML_STORE_PREFIX,
    PIPELINE_API_TOKEN_EXPIRES_MINUTES,
)
from zenml.enums import StackComponentType, StoreType
from zenml.logger import get_logger
from zenml.stack import StackComponent
from zenml.utils.string_utils import format_name_template

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
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
            logger.warning(
                "An API token without an expiration time will be generated "
                "and used to run this pipeline on a schedule. This is very "
                "insecure because the API token cannot be revoked in case "
                "of potential theft without disabling the entire user "
                "account. When deploying a pipeline on a schedule, it is "
                "strongly advised to use a service account API key to "
                "authenticate to the ZenML server instead of your regular "
                "user account. For more information, see "
                "https://docs.zenml.io/how-to/connecting-to-zenml/connect-with-a-service-account"
            )
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
    run_name = format_name_template(run_name_template)

    if run_name == "":
        raise ValueError("Empty run names are not allowed.")

    return run_name


class register_artifact_store_filesystem:
    """Context manager for the artifact_store/filesystem_registry dependency.

    Even though it is rare, sometimes we bump into cases where we are trying to
    load artifacts that belong to an artifact store which is different from
    the active artifact store.

    In cases like this, we will try to instantiate the target artifact store
    by creating the corresponding artifact store Python object, which ends up
    registering the right filesystem in the filesystem registry.

    The problem is, the keys in the filesystem registry are schemes (such as
    "s3://" or "gcs://"). If we have two artifact stores with the same set of
    supported schemes, we might end up overwriting the filesystem that belongs
    to the active artifact store (and its authentication). That's why we have
    to re-instantiate the active artifact store again, so the correct filesystem
    will be restored.
    """

    def __init__(self, target_artifact_store_id: Optional[UUID]) -> None:
        """Initialization of the context manager.

        Args:
            target_artifact_store_id: the ID of the artifact store to load.
        """
        self.target_artifact_store_id = target_artifact_store_id

    def __enter__(self) -> "BaseArtifactStore":
        """Entering the context manager.

        It creates an instance of the target artifact store to register the
        correct filesystem in the registry.

        Returns:
            The target artifact store object.

        Raises:
            RuntimeError: If the target artifact store can not be fetched or
                initiated due to missing dependencies.
        """
        try:
            if self.target_artifact_store_id is not None:
                if (
                    Client().active_stack.artifact_store.id
                    != self.target_artifact_store_id
                ):
                    get_logger(__name__).debug(
                        f"Trying to use the artifact store with ID:"
                        f"'{self.target_artifact_store_id}'"
                        f"which is currently not the active artifact store."
                    )

                artifact_store_model_response = Client().get_stack_component(
                    component_type=StackComponentType.ARTIFACT_STORE,
                    name_id_or_prefix=self.target_artifact_store_id,
                )
                return cast(
                    "BaseArtifactStore",
                    StackComponent.from_model(artifact_store_model_response),
                )
            else:
                return Client().active_stack.artifact_store

        except KeyError:
            raise RuntimeError(
                "Unable to fetch the artifact store with id: "
                f"'{self.target_artifact_store_id}'. Check whether the "
                "artifact store still exists and you have the right "
                "permissions to access it."
            )
        except ImportError:
            raise RuntimeError(
                "Unable to load the implementation of the artifact store with"
                f"id: '{self.target_artifact_store_id}'. Please make sure that "
                "the environment that you are loading this artifact from "
                "has the right dependencies."
            )

    def __exit__(
        self,
        exc_type: Optional[Any],
        exc_value: Optional[Any],
        traceback: Optional[Any],
    ) -> None:
        """Set it back to the original state.

        Args:
            exc_type: The class of the exception
            exc_value: The instance of the exception
            traceback: The traceback of the exception
        """
        if ENV_ZENML_SERVER not in os.environ:
            # As we exit the handler, we have to re-register the filesystem
            # that belongs to the active artifact store as it may have been
            # overwritten.
            Client().active_stack.artifact_store._register()
