#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Utility functions for logging artifact metadata."""

from typing import Dict, Optional

from zenml.exceptions import StepContextError
from zenml.metadata.metadata_types import MetadataType
from zenml.new.steps.step_context import get_step_context


def log_artifact_metadata(
    output_name: Optional[str] = None,
    **kwargs: MetadataType,
) -> None:
    """Log artifact metadata.

    Args:
        output_name: The output name of the artifact to log metadata for. Can
            be omitted if there is only one output artifact.
        **kwargs: Metadata to log.

    Raises:
        RuntimeError: If the function is called outside of a step.
        ValueError: If no output name is provided and there is more than one
            output or if the output name is does not exist.
    """
    if not kwargs:
        return

    try:
        step_context = get_step_context()
    except StepContextError:
        raise RuntimeError("Cannot log artifact metadata outside of a step.")

    try:
        step_context.add_output_metadata(output_name=output_name, **kwargs)
    except StepContextError as e:
        raise ValueError(e)


def log_model_object_metadata(
    output_name: Optional[str] = None,
    description: Optional[str] = None,
    metrics: Optional[Dict[str, MetadataType]] = None,
    hyperparameters: Optional[Dict[str, MetadataType]] = None,
    **kwargs: MetadataType,
) -> None:
    """Log metadata for a model.

    Args:
        output_name: The output name of the artifact to log metadata for. Can
            be omitted if there is only one output artifact.
        description: A description of the model.
        metrics: The metrics to log.
        hyperparameters: The hyperparameters to log.
        **kwargs: Other metadata to log.
    """
    if description:
        kwargs["description"] = description
    if metrics:
        kwargs["metrics"] = metrics
    if hyperparameters:
        kwargs["hyperparameters"] = hyperparameters
    log_artifact_metadata(
        output_name=output_name,
        **kwargs,
    )


def log_deployment_metadata(
    output_name: Optional[str] = None,
    description: Optional[str] = None,
    predict_url: Optional[str] = None,
    explain_url: Optional[str] = None,
    healthcheck_url: Optional[str] = None,
    deployer_ui_url: Optional[str] = None,
    **kwargs: MetadataType,
) -> None:
    """Log metadata for a deployment.

    Args:
        output_name: The output name of the artifact to log metadata for. Can
            be omitted if there is only one output artifact.
        description: A description of the deployment.
        predict_url: The predict URL of the deployment.
        explain_url: The explain URL of the deployment.
        healthcheck_url: The healthcheck URL of the deployment.
        deployer_ui_url: The deployer UI URL of the deployment.
        **kwargs: Other metadata to log.
    """
    if description:
        kwargs["description"] = description
    if predict_url:
        kwargs["predict_url"] = predict_url
    if explain_url:
        kwargs["explain_url"] = explain_url
    if healthcheck_url:
        kwargs["healthcheck_url"] = healthcheck_url
    if deployer_ui_url:
        kwargs["deployer_ui_url"] = deployer_ui_url

    log_artifact_metadata(
        output_name=output_name,
        **kwargs,
    )
