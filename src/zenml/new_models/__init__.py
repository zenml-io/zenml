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

from zenml.new_models.artifact_models import ArtifactRequestModel
from zenml.new_models.artifact_models import (
    ArtifactResponseModel as ArtifactModel,
)
from zenml.new_models.component_models import ComponentRequestModel
from zenml.new_models.component_models import (
    ComponentResponseModel as ComponentModel,
)
from zenml.new_models.flavor_models import FlavorRequestModel
from zenml.new_models.flavor_models import FlavorResponseModel as FlavorModel
from zenml.new_models.pipeline_models import PipelineRequestModel
from zenml.new_models.pipeline_models import (
    PipelineResponseModel as PipelineModel,
)
from zenml.new_models.pipeline_run_models import PipelineRunRequestModel
from zenml.new_models.pipeline_run_models import (
    PipelineRunResponseModel as RunModel,
)
from zenml.new_models.stack_models import StackRequestModel
from zenml.new_models.stack_models import StackResponseModel as StackModel
from zenml.new_models.step_run_models import StepRunRequestModel
from zenml.new_models.step_run_models import (
    StepRunResponseModel as StepRunModel,
)
