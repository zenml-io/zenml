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

from typing import TYPE_CHECKING, Any

from zenml.enums import StackComponentType, TrainingResourceFlavor
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)
from zenml.training_resources import BaseTrainingResource

if TYPE_CHECKING:
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.steps import BaseStep


@register_stack_component_class(
    component_type=StackComponentType.TRAINING_RESOURCE,
    component_flavor=TrainingResourceFlavor.AZUREML,
)
class AzureMLTrainingResource(BaseTrainingResource):
    """Training resource to run a step on AzureML."""

    supports_local_execution = True
    supports_remote_execution = True

    @property
    def flavor(self) -> TrainingResourceFlavor:
        """The training resource flavor."""
        return TrainingResourceFlavor.AZUREML

    def launch(
        self, runtime_configuration: "RuntimeConfiguration", step: "BaseStep"
    ) -> Any:
        """Launches a step on the training resource."""
