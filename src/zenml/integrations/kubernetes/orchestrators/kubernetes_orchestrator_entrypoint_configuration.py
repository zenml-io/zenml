"""Entrypoint configuration for the k8s master/orchestrator pod."""

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

import json
from typing import List, Set

from zenml.entrypoints.step_entrypoint_configuration import (
    INPUT_ARTIFACT_SOURCES_OPTION,
    MATERIALIZER_SOURCES_OPTION,
    STEP_SOURCE_OPTION,
)
from zenml.integrations.kubernetes.orchestrators.kubernetes_step_entrypoint_configuration import (
    RUN_NAME_OPTION,
    KubernetesStepEntrypointConfiguration,
)

PIPELINE_NAME_OPTION = "pipeline_name"
IMAGE_NAME_OPTION = "image_name"
NAMESPACE_OPTION = "kubernetes_namespace"
PIPELINE_CONFIG_OPTION = "pipeline_config"

STEP_SPECIFIC_STEP_ENTRYPOINT_OPTIONS = [
    STEP_SOURCE_OPTION,
    INPUT_ARTIFACT_SOURCES_OPTION,
    MATERIALIZER_SOURCES_OPTION,
]  # options from StepEntrypointConfiguration that change from step to step.


def get_fixed_step_args(
    step_args: List[str], get_fixed: bool = True
) -> List[str]:
    """Get the fixed step args that don't change between steps.

    We want to have them separate so we can send them to the orchestrator pod
    only once.
    """
    fixed_args = []
    for i, arg in enumerate(step_args):
        if not arg.startswith("--"):  # arg is a value, not an option
            continue
        option_and_value = step_args[i : i + 2]  # e.g. ["--name", "Aria"]
        is_fixed = arg[2:] not in STEP_SPECIFIC_STEP_ENTRYPOINT_OPTIONS
        is_correct_category = is_fixed == get_fixed
        if is_correct_category:
            fixed_args += option_and_value
    return fixed_args


def get_step_specific_args(step_args: List[str]) -> List[str]:
    """Get the step-specific args that change from step to step."""
    return get_fixed_step_args(step_args, get_fixed=False)


class KubernetesOrchestratorEntrypointConfiguration:
    """Entrypoint configuration for the k8s master/orchestrator pod."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all the options required for running this entrypoint."""
        options = {
            RUN_NAME_OPTION,
            PIPELINE_NAME_OPTION,
            IMAGE_NAME_OPTION,
            NAMESPACE_OPTION,
            PIPELINE_CONFIG_OPTION,
        }
        return options

    @classmethod
    def get_entrypoint_command(cls) -> List[str]:
        """Returns a command that runs the entrypoint module."""
        command = [
            "python",
            "-m",
            "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator_entrypoint",
        ]
        return command

    @classmethod
    def get_entrypoint_arguments(
        cls,
        run_name: str,
        pipeline_name: str,
        image_name: str,
        kubernetes_namespace: str,
        pb2_pipeline,
        sorted_steps,
        step_dependencies,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with."""

        def _get_step_args(step):
            """Get the entrypoint args for a specific step."""
            return (
                KubernetesStepEntrypointConfiguration.get_entrypoint_arguments(
                    step=step,
                    pb2_pipeline=pb2_pipeline,
                    **{RUN_NAME_OPTION: run_name},
                )
            )

        # Get name, command, and args for each step
        step_names = [step.name for step in sorted_steps]
        step_command = (
            KubernetesStepEntrypointConfiguration.get_entrypoint_command()
        )
        # TODO: handle empty pipelines without steps
        fixed_step_args = get_fixed_step_args(_get_step_args(sorted_steps[0]))
        step_specific_args = {
            step.name: get_step_specific_args(_get_step_args(step))
            for step in sorted_steps
        }  # e.g.: {"trainer": train_step_args, ...}

        # Serialize all complex datatype args into a single JSON string
        pipeline_config = {
            "sorted_steps": step_names,
            "step_command": step_command,
            "fixed_step_args": fixed_step_args,
            "step_specific_args": step_specific_args,
            "step_dependencies": step_dependencies,
        }
        pipeline_config_json = json.dumps(pipeline_config)

        # Define entrypoint args.
        args = [
            f"--{RUN_NAME_OPTION}",
            run_name,
            f"--{PIPELINE_NAME_OPTION}",
            pipeline_name,
            f"--{IMAGE_NAME_OPTION}",
            image_name,
            f"--{NAMESPACE_OPTION}",
            kubernetes_namespace,
            f"--{PIPELINE_CONFIG_OPTION}",
            pipeline_config_json,
        ]

        return args
