#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Step operator pattern: selective GPU offloading to Run:AI."""

from steps.data_loader import data_loader
from steps.gpu_trainer import gpu_trainer

from zenml import pipeline


@pipeline(
    enable_cache=False,
)
def gpu_training_pipeline():
    """Step operator pattern: selective GPU offloading to Run:AI.

    This pipeline demonstrates the step operator pattern where:
    - data_loader: Runs on Kubernetes (CPU) - lightweight data preparation
    - gpu_trainer: Offloaded to Run:AI with fractional GPU - heavy training

    This pattern is ideal when only specific steps need GPU resources,
    avoiding the cost of running the entire pipeline on GPU nodes.
    """
    data = data_loader()
    gpu_trainer(data=data)
