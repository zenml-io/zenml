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
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.enums import PluginSubType
from zenml.models import TriggerExecutionResponse

# -------------------- Configuration Models ----------------------------------


class PipelineRunActionConfiguration(ActionConfig):
    """Configuration class to configure a pipeline run action."""

    pipeline_deployment_id: UUID
    pipeline_config: Optional[PipelineRunConfiguration] = None


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

    def run(
        self,
        config: Dict[str, Any],
        trigger_execution: TriggerExecutionResponse,
    ) -> None:
        from zenml.zen_server.utils import zen_store

        config_obj: PipelineRunActionConfiguration = self.config_class(
            **config
        )
        deployment = zen_store().get_deployment(
            config_obj.pipeline_deployment_id
        )
        print("Running deployment:", deployment)


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
