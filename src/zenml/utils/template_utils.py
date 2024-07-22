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
"""Utilities for run templates."""

from enum import Enum
from typing import Any, Dict

from pydantic import create_model

from zenml.client import Client
from zenml.config import ResourceSettings
from zenml.config.base_settings import BaseSettings
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.models import (
    FlavorFilter,
    PipelineDeploymentResponse,
    StackResponse,
)
from zenml.stack import Flavor

logger = get_logger(__name__)


def generate_config_template(
    deployment: PipelineDeploymentResponse,
) -> Dict[str, Any]:
    """Generate a run configuration template for a deployment.

    Args:
        deployment: The deployment.

    Returns:
        The run configuration template.
    """
    steps_configs = {
        name: step.config.model_dump(
            include=set(StepConfigurationUpdate.model_fields),
            exclude={"name", "outputs"},
        )
        for name, step in deployment.step_configurations.items()
    }

    for config in steps_configs.values():
        config["settings"].pop("docker", None)

    pipeline_config = deployment.pipeline_configuration.model_dump(
        include=set(PipelineRunConfiguration.model_fields),
        exclude={"schedule", "build", "parameters"},
    )

    pipeline_config["settings"].pop("docker", None)

    config_template = {
        "run_name": deployment.run_name_template,
        "steps": steps_configs,
        **pipeline_config,
    }
    return config_template


def generate_config_schema(
    deployment: PipelineDeploymentResponse, stack: StackResponse
) -> Dict[str, Any]:
    """Generate a run configuration schema for the deployment and stack.

    Args:
        deployment: The deployment.
        stack: The stack.

    Returns:
        The generated schema dictionary.
    """
    experiment_trackers = []
    step_operators = []

    settings_fields: Dict[str, Any] = {"resources": (ResourceSettings, None)}
    for component_list in stack.components.values():
        assert len(component_list) == 1
        component = component_list[0]
        flavors = Client().zen_store.list_flavors(
            FlavorFilter(name=component.flavor, type=component.type)
        )
        assert len(flavors) == 1
        flavor_model = flavors[0]
        flavor = Flavor.from_model(flavor_model)

        for class_ in flavor.config_class.__mro__[1:]:
            # Ugly hack to get the settings class of a flavor without having
            # the integration installed. This is based on the convention that
            # the static config of a stack component should always inherit
            # from the dynamic settings.
            if issubclass(class_, BaseSettings):
                if len(class_.model_fields) > 0:
                    settings_key = f"{component.type}.{component.flavor}"
                    settings_fields[settings_key] = (
                        class_,
                        None,
                    )

                break

        if component.type == StackComponentType.EXPERIMENT_TRACKER:
            experiment_trackers.append(component.name)
        if component.type == StackComponentType.STEP_OPERATOR:
            step_operators.append(component.name)

    settings_model = create_model("Settings", **settings_fields)

    generic_step_fields: Dict[str, Any] = {}

    for key, field_info in StepConfigurationUpdate.model_fields.items():
        if key in [
            "name",
            "outputs",
            "step_operator",
            "experiment_tracker",
            "parameters",
        ]:
            continue

        generic_step_fields[key] = (field_info.annotation, field_info)

    if experiment_trackers:
        experiment_tracker_enum = Enum(  # type: ignore[misc]
            "ExperimentTrackers", {e: e for e in experiment_trackers}
        )
        generic_step_fields["experiment_tracker"] = (
            experiment_tracker_enum,
            None,
        )
    if step_operators:
        step_operator_enum = Enum(  # type: ignore[misc]
            "StepOperators", {s: s for s in step_operators}
        )
        generic_step_fields["step_operator"] = (step_operator_enum, None)

    generic_step_fields["settings"] = (settings_model, None)

    all_steps: Dict[str, Any] = {}
    for name, step in deployment.step_configurations.items():
        step_fields = generic_step_fields.copy()
        if step.config.parameters:
            parameter_fields: Dict[str, Any] = {
                name: (Any, None) for name in step.config.parameters
            }
            parameters_class = create_model(
                f"{name}_parameters", **parameter_fields
            )
            step_fields["parameters"] = (parameters_class, None)

        step_model = create_model(name, **step_fields)
        all_steps[name] = (step_model, None)

    all_steps_model = create_model("Steps", **all_steps)

    top_level_fields: Dict[str, Any] = {}

    for key, field_info in PipelineRunConfiguration.model_fields.items():
        if key in ["schedule", "build", "steps", "settings", "parameters"]:
            continue

        top_level_fields[key] = (field_info.annotation, field_info)

    top_level_fields["settings"] = (settings_model, None)
    top_level_fields["steps"] = (all_steps_model, None)

    return create_model("Result", **top_level_fields).model_json_schema()  # type: ignore[no-any-return]
