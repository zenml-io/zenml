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
from typing import ClassVar, Type
from uuid import UUID

from zenml.action_plans.base_action_plan import (
    ActionPlanConfig,
    BaseActionPlanFlavor,
    BaseActionPlan,
)
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration

# -------------------- Configuration Models ----------------------------------


class PipelineRunActionPlanConfiguration(ActionPlanConfig):
    """Configuration class to configure a pipeline run action."""

    pipeline_build_id: UUID
    pipeline_config: PipelineRunConfiguration


# -------------------- Pipeline Run Plugin -----------------------------------


class PipelineRunActionPlan(BaseActionPlan):
    """Handler for all github events."""

    @property
    def config_class(self) -> Type[PipelineRunActionPlanConfiguration]:
        """Returns the `BasePluginConfig` config.

        Returns:
            The configuration.
        """
        return PipelineRunActionPlanConfiguration


# -------------------- Pipeline Run Flavor -----------------------------------


class PipelineRunActionPlanFlavor(BaseActionPlanFlavor):
    """Enables users to configure pipeline run action."""

    FLAVOR: ClassVar[str] = "builtin"
    PLUGIN_CLASS: ClassVar[
        Type[PipelineRunActionPlan]
    ] = PipelineRunActionPlan

    # EventPlugin specific
    ACTION_PLAN_CONFIG_CLASS: ClassVar[
        Type[PipelineRunActionPlanConfiguration]
    ] = PipelineRunActionPlanConfiguration
