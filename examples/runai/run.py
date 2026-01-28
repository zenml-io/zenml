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
"""Run the Run:AI step operator example pipeline."""

from pipelines.gpu_training_pipeline import gpu_training_pipeline

if __name__ == "__main__":
    # Run the pipeline demonstrating step operator pattern:
    #
    # 1. data_loader: Runs on Kubernetes (CPU)
    #    - Generates synthetic training data
    #    - Uses base docker settings with numpy only
    #
    # 2. gpu_trainer: Offloaded to Run:AI with GPU
    #    - Trains PyTorch model on GPU
    #    - Uses custom PyTorch GPU image
    #    - Run:AI settings: 0.5 GPU, 2-4 CPU cores, 4-8GB RAM
    #    - Preemptible workload with retry support
    #
    # This pattern is ideal when only specific steps need GPU,
    # avoiding the cost of running the entire pipeline on GPU nodes.
    gpu_training_pipeline()
