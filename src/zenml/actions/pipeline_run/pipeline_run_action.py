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
"""Example file of what an action Plugin could look like."""

from typing import Any, ClassVar, Dict, Optional, Type
from uuid import UUID

from zenml.actions.base_action import (
    ActionConfig,
    BaseActionFlavor,
    BaseActionHandler,
)
from zenml.config.global_config import GlobalConfiguration
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.enums import PluginSubType
from zenml.logger import get_logger
from zenml.models import (
    ActionRequest,
    ActionResponse,
    ActionUpdate,
    TriggerExecutionResponse,
)
from zenml.models.v2.base.base import BaseResponse
from zenml.zen_server.auth import AuthContext
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.template_execution.utils import run_template
from zenml.zen_server.utils import server_config

logger = get_logger(__name__)

# -------------------- Configuration Models ----------------------------------


class PipelineRunActionConfiguration(ActionConfig):
    """Configuration class to configure a pipeline run action."""

    template_id: UUID
    run_config: Optional[PipelineRunConfiguration] = None


# -------------------- Pipeline Run Plugin -----------------------------------


class PipelineRunActionHandler(BaseActionHandler):
    """Action handler for running pipelines."""

    @property
    def config_class(self) -> Type[PipelineRunActionConfiguration]:
        """Returns the `BasePluginConfig` config.

        Returns:
            The configuration.
        """
        return PipelineRunActionConfiguration

    @property
    def flavor_class(self) -> Type[BaseActionFlavor]:
        """Returns the flavor class of the plugin.

        Returns:
            The flavor class of the plugin.
        """
        return PipelineRunActionFlavor

    def run(
        self,
        config: ActionConfig,
        trigger_execution: TriggerExecutionResponse,
        auth_context: AuthContext,
    ) -> None:
        """Execute an action.

        Args:
            config: The action configuration
            trigger_execution: The trigger execution
            auth_context: Authentication context with an API token that can be
                used by external workloads to authenticate with the server
                during the execution of the action. This API token is associated
                with the service account that was configured for the trigger
                that activated the action and has a validity defined by the
                trigger's authentication window.
        """
        from zenml.zen_server.utils import zen_store

        assert isinstance(config, PipelineRunActionConfiguration)

        template = zen_store().get_run_template(config.template_id)
        logger.debug("Running template:", template)
        run_template(
            template=template,
            run_config=config.run_config,
            auth_context=auth_context,
            sync=True,
        )

    def _validate_configuration(
        self, config: PipelineRunActionConfiguration
    ) -> None:
        """Validate a pipeline run action configuration.

        Args:
            config: Pipeline run action configuration.

        Raises:
            ValueError: In case no deployment can be found with the deployment_id
        """
        zen_store = GlobalConfiguration().zen_store

        try:
            zen_store.get_run_template(template_id=config.template_id)
        except KeyError:
            raise ValueError(
                f"No template found with id {config.template_id}."
            )

    def _validate_action_request(
        self, action: ActionRequest, config: ActionConfig
    ) -> None:
        """Validate an action request before it is created in the database.

        Args:
            action: Action request.
            config: Action configuration instantiated from the request.
        """
        assert isinstance(config, PipelineRunActionConfiguration)

        self._validate_configuration(config)

        # If an expiration window is not set, we set it to the default value
        if action.auth_window is None:
            action.auth_window = server_config().pipeline_run_auth_window

    def _validate_action_update(
        self,
        action: ActionResponse,
        config: ActionConfig,
        action_update: ActionUpdate,
        config_update: ActionConfig,
    ) -> None:
        """Validate an action update before it is reflected in the database.

        Args:
            action: Original action before the update.
            config: Action configuration instantiated from the original
                action.
            action_update: Action update request.
            config_update: Action configuration instantiated from the
                updated action.
        """
        assert isinstance(config, PipelineRunActionConfiguration)

        self._validate_configuration(config)

    def extract_resources(
        self,
        action_config: ActionConfig,
        hydrate: bool = False,
    ) -> Dict[ResourceType, BaseResponse[Any, Any, Any]]:
        """Extract related resources for this action.

        Args:
            action_config: Action configuration from which to extract related
                resources.
            hydrate: Flag deciding whether to hydrate the resources.

        Returns:
            List of resources related to the action.

        Raises:
            ValueError: In case the specified template does not exist.
        """
        assert isinstance(action_config, PipelineRunActionConfiguration)

        zen_store = GlobalConfiguration().zen_store

        try:
            template = zen_store.get_run_template(
                template_id=action_config.template_id, hydrate=hydrate
            )
        except KeyError:
            raise ValueError(
                f"No template found with id {action_config.template_id}."
            )

        resources: Dict[ResourceType, BaseResponse[Any, Any, Any]] = {
            ResourceType.RUN_TEMPLATE: template
        }

        if template.pipeline is not None:
            pipeline = zen_store.get_pipeline(
                pipeline_id=template.pipeline.id, hydrate=hydrate
            )
            resources[ResourceType.PIPELINE] = pipeline

        return resources


# -------------------- Pipeline Run Flavor -----------------------------------


class PipelineRunActionFlavor(BaseActionFlavor):
    """Enables users to configure pipeline run action."""

    FLAVOR: ClassVar[str] = "builtin"
    SUBTYPE: ClassVar[PluginSubType] = PluginSubType.PIPELINE_RUN
    PLUGIN_CLASS: ClassVar[Type[PipelineRunActionHandler]] = (
        PipelineRunActionHandler
    )

    # EventPlugin specific
    ACTION_CONFIG_CLASS: ClassVar[Type[PipelineRunActionConfiguration]] = (
        PipelineRunActionConfiguration
    )
