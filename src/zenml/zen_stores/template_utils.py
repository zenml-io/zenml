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
"""Utilities for run templates."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import create_model
from pydantic.fields import FieldInfo

from zenml.config import ResourceSettings
from zenml.config.base_settings import BaseSettings
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.source import SourceWithValidator
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.stack import Flavor
from zenml.zen_stores.schemas import PipelineDeploymentSchema

logger = get_logger(__name__)


def validate_deployment_is_templatable(
    deployment: PipelineDeploymentSchema,
) -> None:
    """Validate that a deployment is templatable.

    Args:
        deployment: The deployment to validate.

    Raises:
        ValueError: If the deployment is not templatable.
    """
    if not deployment.build:
        raise ValueError(
            "Unable to create run template as there is no associated build."
        )

    if not deployment.build.stack:
        raise ValueError(
            "Unable to create run template as the associated build has no "
            "stack reference."
        )

    for component in deployment.build.stack.components:
        if not component.flavor_schema:
            raise ValueError(
                "Unable to create run template as a component of the "
                "associated stack has no flavor."
            )

        if component.flavor_schema.workspace_id:
            raise ValueError(
                "Unable to create run template as a component of the "
                "associated stack has a custom flavor."
            )

        flavor_model = component.flavor_schema.to_model()
        flavor = Flavor.from_model(flavor_model)
        component_config = flavor.config_class(
            **component.to_model(include_metadata=True).configuration
        )

        if component_config.is_local:
            raise ValueError(
                "Unable to create run template as the stack of the associated "
                "build contains local components."
            )


def generate_config_template(
    deployment: PipelineDeploymentSchema,
) -> Dict[str, Any]:
    """Generate a run configuration template for a deployment.

    Args:
        deployment: The deployment.

    Returns:
        The run configuration template.
    """
    deployment_model = deployment.to_model(include_metadata=True)

    steps_configs = {
        name: step.config.model_dump(
            include=set(StepConfigurationUpdate.model_fields),
            exclude={"name", "outputs"},
        )
        for name, step in deployment_model.step_configurations.items()
    }

    for config in steps_configs.values():
        config["settings"].pop("docker", None)

    pipeline_config = deployment_model.pipeline_configuration.model_dump(
        include=set(PipelineRunConfiguration.model_fields),
        exclude={"schedule", "build", "parameters"},
    )

    pipeline_config["settings"].pop("docker", None)

    config_template = {
        "run_name": deployment_model.run_name_template,
        "steps": steps_configs,
        **pipeline_config,
    }
    return config_template


def generate_config_schema(
    deployment: PipelineDeploymentSchema,
) -> Dict[str, Any]:
    """Generate a run configuration schema for the deployment and stack.

    Args:
        deployment: The deployment schema.

    Returns:
        The generated schema dictionary.
    """
    # Config schema can only be generated for a runnable template, so this is
    # guaranteed by checks in the run template schema
    assert deployment.build
    assert deployment.build.stack

    stack = deployment.build.stack
    experiment_trackers = []
    step_operators = []

    settings_fields: Dict[str, Any] = {"resources": (ResourceSettings, None)}
    for component in stack.components:
        if not component.flavor_schema:
            continue

        flavor_model = component.flavor_schema.to_model()
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
                        Optional[class_],
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

        if field_info.annotation == Optional[SourceWithValidator]:
            generic_step_fields[key] = (Optional[str], None)
        else:
            generic_step_fields[key] = (field_info.annotation, field_info)

    if experiment_trackers:
        experiment_tracker_enum = Enum(  # type: ignore[misc]
            "ExperimentTrackers", {e: e for e in experiment_trackers}
        )
        generic_step_fields["experiment_tracker"] = (
            Optional[experiment_tracker_enum],
            None,
        )
    if step_operators:
        step_operator_enum = Enum(  # type: ignore[misc]
            "StepOperators", {s: s for s in step_operators}
        )
        generic_step_fields["step_operator"] = (
            Optional[step_operator_enum],
            None,
        )

    generic_step_fields["settings"] = (Optional[settings_model], None)

    all_steps: Dict[str, Any] = {}
    all_steps_required = False
    for name, step in deployment.to_model(
        include_metadata=True
    ).step_configurations.items():
        step_fields = generic_step_fields.copy()
        if step.config.parameters:
            parameter_fields: Dict[str, Any] = {
                name: (Any, FieldInfo(default=...))
                for name in step.config.parameters
            }
            parameters_class = create_model(
                f"{name}_parameters", **parameter_fields
            )
            step_fields["parameters"] = (
                parameters_class,
                FieldInfo(default=...),
            )

        step_model = create_model(name, **step_fields)

        if step.config.parameters:
            # This step has required parameters -> we make this attribute
            # required and also the parent attribute so these parameters must
            # always be included
            all_steps_required = True
            all_steps[name] = (step_model, FieldInfo(default=...))
        else:
            all_steps[name] = (Optional[step_model], FieldInfo(default=None))

    all_steps_model = create_model("Steps", **all_steps)

    top_level_fields: Dict[str, Any] = {}

    for key, field_info in PipelineRunConfiguration.model_fields.items():
        if key in ["schedule", "build", "steps", "settings", "parameters"]:
            continue

        if field_info.annotation == Optional[SourceWithValidator]:
            top_level_fields[key] = (Optional[str], None)
        else:
            top_level_fields[key] = (field_info.annotation, field_info)

    top_level_fields["settings"] = (Optional[settings_model], None)

    if all_steps_required:
        top_level_fields["steps"] = (all_steps_model, FieldInfo(default=...))
    else:
        top_level_fields["steps"] = (
            Optional[all_steps_model],
            FieldInfo(default=None),
        )

    return create_model("Result", **top_level_fields).model_json_schema()  # type: ignore[no-any-return]
