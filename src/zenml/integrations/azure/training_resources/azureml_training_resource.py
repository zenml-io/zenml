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

from typing import TYPE_CHECKING, Any, List

from azureml.core import (
    ComputeTarget,
    Environment,
    Experiment,
    ScriptRunConfig,
    Workspace,
)
from azureml.core.authentication import AzureCliAuthentication

from zenml.enums import StackComponentType, TrainingResourceFlavor
from zenml.repository import Repository
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)
from zenml.training_resources import BaseTrainingResource

if TYPE_CHECKING:
    pass


@register_stack_component_class(
    component_type=StackComponentType.TRAINING_RESOURCE,
    component_flavor=TrainingResourceFlavor.AZUREML,
)
class AzureMLTrainingResource(BaseTrainingResource):
    """Training resource to run a step on AzureML."""

    supports_local_execution = True
    supports_remote_execution = True
    subscription_id: str
    resource_group: str
    workspace_name: str
    compute_target_name: str

    @property
    def flavor(self) -> TrainingResourceFlavor:
        """The training resource flavor."""
        return TrainingResourceFlavor.AZUREML

    def launch(
            self,
            pipeline_name: str,
            run_name: str,
            entrypoint_command: List[str]
    ) -> Any:
        """Launches a step on the training resource."""

        auth = AzureCliAuthentication()

        ws = Workspace.get(
            subscription_id=self.subscription_id,
            resource_group=self.resource_group,
            name=self.workspace_name,
            auth=auth,
        )

        env = Environment.from_dockerfile("dockerzenml", "Dockerfile")
        experiment = Experiment(workspace=ws, name=pipeline_name)
        compute_target = ComputeTarget(
            workspace=ws, name=self.compute_target_name
        )

        src = ScriptRunConfig(
            source_directory=str(Repository().root),
            compute_target=compute_target,
            environment=env,
            command=entrypoint_command
        )
        # submit a run
        run = experiment.submit(config=src)
        run.display_name = run_name
        run.wait_for_completion(show_output=True)
