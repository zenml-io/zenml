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
    ENV_ZENML_ACTIVE_PROJECT_ID,
    ENV_ZENML_ACTIVE_STACK_ID,
    ENV_ZENML_DISABLE_CREDENTIALS_DISK_CACHING,
    ENV_ZENML_PIPELINE_RUN_API_TOKEN_EXPIRATION,
    ENV_ZENML_SERVER,
    ENV_ZENML_STORE_PREFIX,
    ZENML_PIPELINE_RUN_API_TOKEN_EXPIRATION,
)
from zenml.enums import APITokenType, AuthScheme, StackComponentType, StoreType
from zenml.logger import get_logger
from zenml.stack import StackComponent

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore


def get_orchestrator_run_name(
    pipeline_name: str, max_length: Optional[int] = None
) -> str:
    """Gets an orchestrator run name.

    This run name is not the same as the ZenML run name but can instead be
    used to display in the orchestrator UI.

    Args:
        pipeline_name: Name of the pipeline that will run.
        max_length: Maximum length of the generated name.

    Raises:
        ValueError: If the max length is below 8 characters.

    Returns:
        The orchestrator run name.
    """
    suffix_length = 32
    pipeline_name = f"{pipeline_name}_"

    if max_length:
        if max_length < 8:
            raise ValueError(
                "Maximum length for orchestrator run name must be 8 or above."
            )

        # Make sure we always have a certain suffix to guarantee no overlap
        # with other runs
        suffix_length = min(32, max(8, max_length - len(pipeline_name)))
        pipeline_name = pipeline_name[: (max_length - suffix_length)]

    suffix = "".join(random.choices("0123456789abcdef", k=suffix_length))

    return f"{pipeline_name}{suffix}"


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
    schedule_id: Optional[UUID] = None,
    pipeline_run_id: Optional[UUID] = None,
) -> Dict[str, str]:
    """Gets environment variables to set for mirroring the active config.

    If a schedule ID, pipeline run ID or step run ID is given, and the current
    client is not authenticated to a server with an API key, the environment
    variables will be updated to include a newly generated workload API token
    that will be valid for the duration of the schedule, pipeline run, or step
    run instead of the current API token used to authenticate the client.

    Args:
        schedule_id: Optional schedule ID to use to generate a new API token.
        pipeline_run_id: Optional pipeline run ID to use to generate a new API
            token.

    Returns:
        Environment variable dict.
    """
    from zenml.login.credentials_store import get_credentials_store
    from zenml.zen_stores.rest_zen_store import RestZenStore

    global_config = GlobalConfiguration()
    environment_vars = global_config.get_config_environment_vars()

    if (
        global_config.store_configuration.type == StoreType.REST
        and global_config.zen_store.get_store_info().auth_scheme
        != AuthScheme.NO_AUTH
    ):
        credentials_store = get_credentials_store()
        url = global_config.store_configuration.url
        api_token = credentials_store.get_token(url, allow_expired=False)
        if schedule_id or pipeline_run_id:
            assert isinstance(global_config.zen_store, RestZenStore)

            # The user has the option to manually set an expiration for the API
            # token generated for a pipeline run. In this case, we generate a new
            # generic API token that will be valid for the indicated duration.
            if (
                pipeline_run_id
                and ZENML_PIPELINE_RUN_API_TOKEN_EXPIRATION != 0
            ):
                logger.warning(
                    f"An unscoped API token will be generated for this pipeline "
                    f"run that will expire after "
                    f"{ZENML_PIPELINE_RUN_API_TOKEN_EXPIRATION} "
                    f"seconds instead of being scoped to the pipeline run "
                    f"and not having an expiration time. This is more insecure "
                    f"because the API token will remain valid even after the "
                    f"pipeline run completes its execution. This option has "
                    "been explicitly enabled by setting the "
                    f"{ENV_ZENML_PIPELINE_RUN_API_TOKEN_EXPIRATION} environment "
                    f"variable"
                )
                new_api_token = global_config.zen_store.get_api_token(
                    token_type=APITokenType.GENERIC,
                    expires_in=ZENML_PIPELINE_RUN_API_TOKEN_EXPIRATION,
                )

            else:
                # If a schedule ID, pipeline run ID or step run ID is supplied,
                # we need to fetch a new workload API token scoped to the
                # schedule, pipeline run or step run.

                # If only a schedule is given, the pipeline run credentials will
                # be valid for the entire duration of the schedule.
                api_key = credentials_store.get_api_key(url)
                if not api_key and not pipeline_run_id:
                    logger.warning(
                        "An API token without an expiration time will be generated "
                        "and used to run this pipeline on a schedule. This is very "
                        "insecure because the API token will be valid for the "
                        "entire lifetime of the schedule and can be used to access "
                        "your user account if accidentally leaked. When deploying "
                        "a pipeline on a schedule, it is strongly advised to use a "
                        "service account API key to authenticate to the ZenML "
                        "server instead of your regular user account. For more "
                        "information, see "
                        "https://docs.zenml.io/how-to/manage-zenml-server/connecting-to-zenml/connect-with-a-service-account"
                    )

                # The schedule, pipeline run or step run credentials are scoped to
                # the schedule, pipeline run or step run and will only be valid for
                # the duration of the schedule/pipeline run/step run.
                new_api_token = global_config.zen_store.get_api_token(
                    token_type=APITokenType.WORKLOAD,
                    schedule_id=schedule_id,
                    pipeline_run_id=pipeline_run_id,
                )

            environment_vars[ENV_ZENML_STORE_PREFIX + "API_TOKEN"] = (
                new_api_token
            )
        elif api_token:
            # For all other cases, the pipeline run environment is configured
            # with the current access token.
            environment_vars[ENV_ZENML_STORE_PREFIX + "API_TOKEN"] = (
                api_token.access_token
            )

    # Disable credentials caching to avoid storing sensitive information
    # in the pipeline run environment
    environment_vars[ENV_ZENML_DISABLE_CREDENTIALS_DISK_CACHING] = "true"

    # Make sure to use the correct active stack/project which might come
    # from a .zen repository and not the global config
    environment_vars[ENV_ZENML_ACTIVE_STACK_ID] = str(
        Client().active_stack_model.id
    )
    environment_vars[ENV_ZENML_ACTIVE_PROJECT_ID] = str(
        Client().active_project.id
    )

    return environment_vars


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
