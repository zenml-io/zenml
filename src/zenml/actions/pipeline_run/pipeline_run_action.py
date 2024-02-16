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
from zenml.models import TriggerExecutionResponse
from zenml.models.v2.base.base import BaseResponse
from zenml.zen_server.rbac.models import (  # TODO: Maybe we move these into a common place?
    ResourceType,
)

# -------------------- Configuration Models ----------------------------------


class PipelineRunActionConfiguration(ActionConfig):
    """Configuration class to configure a pipeline run action."""

    pipeline_deployment_id: UUID
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
    ) -> None:
        """Execute an action.

        Args:
            config: The action configuration
            trigger_execution: The trigger execution
        """
        from zenml.zen_server.utils import zen_store

        assert isinstance(config, PipelineRunActionConfiguration)

        deployment = zen_store().get_deployment(config.pipeline_deployment_id)
        print("Running deployment:", deployment)
        # TODO: Call this
        # from zenml.zen_server.pipeline_deployment.utils import redeploy_pipeline
        # redeploy_pipeline(deployment=deployment, run_config=config_obj.run_config)

    def extract_resources(
        self,
        action_config: ActionConfig,
    ) -> Dict[ResourceType, BaseResponse[Any, Any, Any]]:
        """Extract related resources for this action.

        Args:
            action_config: Action configuration from which to extract related
                resources.

        Returns:
            List of resources related to the action.
        """
        assert isinstance(action_config, PipelineRunActionConfiguration)

        deployment_id = action_config.pipeline_deployment_id
        zen_store = GlobalConfiguration().zen_store

        try:
            deployment = zen_store.get_deployment(deployment_id=deployment_id)
        except KeyError:
            raise ValueError(f"No deployment found with id {deployment_id}.")

        resources: Dict[ResourceType, BaseResponse[Any, Any, Any]] = {
            ResourceType.PIPELINE_DEPLOYMENT: deployment
        }

        if deployment.pipeline is not None:
            pipeline = zen_store.get_pipeline(
                pipeline_id=deployment.pipeline.id
            )
            resources[ResourceType.PIPELINE] = pipeline

        return resources


# -------------------- Pipeline Run Flavor -----------------------------------


class PipelineRunActionFlavor(BaseActionFlavor):
    """Enables users to configure pipeline run action."""

    FLAVOR: ClassVar[str] = "builtin"
    SUBTYPE: ClassVar[PluginSubType] = PluginSubType.PIPELINE_RUN
    PLUGIN_CLASS: ClassVar[
        Type[PipelineRunActionHandler]
    ] = PipelineRunActionHandler

    # EventPlugin specific
    ACTION_CONFIG_CLASS: ClassVar[
        Type[PipelineRunActionConfiguration]
    ] = PipelineRunActionConfiguration
