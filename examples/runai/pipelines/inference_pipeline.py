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
"""Inference pipeline for Run:AI deployer example."""

from typing import Dict, List

from steps.inference import predict

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.config.docker_settings import DockerBuildConfig, DockerBuildOptions
from zenml.integrations.runai.flavors import RunAIDeployerSettings

# Run:AI deployer settings for inference workloads
runai_deployer_settings = RunAIDeployerSettings(
    # Fractional GPU for cost-effective inference
    gpu_portion_request=0.25,
    gpu_request_type="portion",
    # CPU resources
    cpu_core_request=1.0,
    cpu_memory_request="2Gi",
    # Autoscaling configuration
    min_replicas=1,
    max_replicas=3,
    # Metadata
    labels={"app": "zenml-inference", "framework": "pytorch"},
    environment_variables={"LOG_LEVEL": "INFO"},
)


@pipeline(
    enable_cache=False,
    settings={
        "deployer": runai_deployer_settings,
        "docker": DockerSettings(
            parent_image="safoinext/zenml:runai",
            build_config=DockerBuildConfig(
                build_options=DockerBuildOptions(platform="linux/amd64"),
            ),
        ),
    },
)
def inference_pipeline(
    features: List[float] = [0.0, 0.0, 0.0, 0.0],
) -> Dict[str, float]:
    """Inference pipeline deployable on Run:AI.

    This pipeline can be deployed as an HTTP endpoint on Run:AI using:

    CLI:
        zenml pipeline deploy pipelines.inference_pipeline --name my-service

    SDK:
        deployment = inference_pipeline.deploy(deployment_name="my-service")

    Once deployed, invoke via:
        zenml deployment invoke my-service --features='[0.5, -0.3, 1.2, 0.8]'

    Or via HTTP:
        curl -X POST <URL>/invoke \\
            -H "Content-Type: application/json" \\
            -d '{"parameters": {"features": [0.5, -0.3, 1.2, 0.8]}}'

    Args:
        features: List of input features for prediction. Must have default value
            for deployment compatibility.

    Returns:
        Dictionary containing prediction results (prediction and probability).
    """
    return predict(features=features)
