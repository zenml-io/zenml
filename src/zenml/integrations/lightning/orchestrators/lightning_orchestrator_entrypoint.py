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
"""Entrypoint of the Lightning master/orchestrator STUDIO."""

import argparse
import os
from typing import Dict, cast

from lightning_sdk import Machine, Studio

from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_WHEEL_PACKAGE_NAME,
)
from zenml.enums import ExecutionStatus
from zenml.integrations.lightning.flavors.lightning_orchestrator_flavor import (
    LightningOrchestratorSettings,
)
from zenml.integrations.lightning.orchestrators.lightning_orchestrator import (
    ENV_ZENML_LIGHTNING_ORCHESTRATOR_RUN_ID,
    LightningOrchestrator,
)
from zenml.integrations.lightning.orchestrators.lightning_orchestrator_entrypoint_config import (
    LightningEntrypointConfiguration,
)
from zenml.integrations.lightning.orchestrators.utils import (
    gather_requirements,
    sanitize_studio_name,
)
from zenml.logger import get_logger
from zenml.orchestrators.dag_runner import ThreadedDagRunner

logger = get_logger(__name__)


LIGHTNING_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH = "."


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_name", type=str, required=True)
    parser.add_argument("--deployment_id", type=str, required=True)
    parser.add_argument("--wheel_package", type=str, required=True)
    return parser.parse_args()


def main() -> None:
    """Entrypoint of the Lightning master/orchestrator STUDIO.

    This is the entrypoint of the Lightning master/orchestrator STUDIO. It is
    responsible for provisioning the STUDIO and running the pipeline steps in
    separate STUDIOs.

    Raises:
        TypeError: If the active stack's orchestrator is not an instance of
            LightningOrchestrator.
        ValueError: If the active stack's container registry is None.
    """
    # Log to the container's stdout so it can be streamed by the client.
    logger.info("Lightning orchestrator STUDIO started.")

    # Parse / extract args.
    args = parse_args()

    orchestrator_run_id = os.environ.get(
        ENV_ZENML_LIGHTNING_ORCHESTRATOR_RUN_ID
    )
    wheel_package_name = os.environ.get(ENV_ZENML_WHEEL_PACKAGE_NAME)
    if not orchestrator_run_id or not wheel_package_name:
        raise ValueError(
            f"Environment variable '{ENV_ZENML_LIGHTNING_ORCHESTRATOR_RUN_ID}' or '{ENV_ZENML_WHEEL_PACKAGE_NAME}' is not set."
        )

    logger.info(f"Orchestrator run id: {orchestrator_run_id}")
    logger.info(f"Wheel package name: {wheel_package_name}")
    logger.info(f"args: {args}")

    deployment = Client().get_deployment(args.deployment_id)

    pipeline_dag = {
        step_name: step.spec.upstream_steps
        for step_name, step in deployment.step_configurations.items()
    }
    command = LightningEntrypointConfiguration.get_entrypoint_command()

    active_stack = Client().active_stack

    orchestrator = active_stack.orchestrator
    if not isinstance(orchestrator, LightningOrchestrator):
        raise TypeError(
            "The active stack's orchestrator is not an instance of LightningOrchestrator."
        )

    # Set up credentials
    orchestrator._get_lightning_client(deployment)
    orchestrator.package_name = wheel_package_name

    pipeline_settings = cast(
        LightningOrchestratorSettings, orchestrator.get_settings(deployment)
    )

    # Gather the requirements
    pipeline_docker_settings = (
        deployment.pipeline_configuration.docker_settings
    )
    pipeline_requirements = gather_requirements(pipeline_docker_settings)
    pipeline_requirements_to_string = " ".join(
        f'"{req}"' for req in pipeline_requirements
    )

    unique_resource_configs: Dict[str, str] = {}
    main_studio_name = sanitize_studio_name(
        f"zenml_{orchestrator_run_id}_pipeline"
    )
    for step_name, step in deployment.step_configurations.items():
        step_settings = cast(
            LightningOrchestratorSettings,
            orchestrator.get_settings(step),
        )
        unique_resource_configs[step_name] = main_studio_name
        if pipeline_settings.machine_type != step_settings.machine_type:
            unique_resource_configs[step_name] = (
                f"zenml-{orchestrator_run_id}_{step_name}"
            )

    logger.info(f"Creating main studio: {main_studio_name}")
    main_studio = Studio(name=main_studio_name)
    if pipeline_settings.machine_type:
        main_studio.start(Machine(pipeline_settings.machine_type))
    else:
        main_studio.start()

    logger.info(
        f"Uploading wheel package {args.wheel_package.rsplit('/', 1)[-1]} and installing dependencies on main studio {main_studio_name}"
    )
    main_studio.upload_file(args.wheel_package.rsplit("/", 1)[-1])
    main_studio.upload_file(
        ".lightning_studio/.studiorc",
        remote_path=".lightning_studio/.studiorc",
    )
    main_studio.run("pip install uv")
    main_studio.run(f"uv pip install {pipeline_requirements_to_string}")
    main_studio.run(
        "pip uninstall zenml -y && pip install git+https://github.com/zenml-io/zenml.git@feature/lightening-studio-orchestrator"
    )
    logger.info(
        f"Installing wheel package {args.wheel_package.rsplit('/', 1)[-1]} on main studio {main_studio_name}"
    )
    main_studio.run(f"pip install {args.wheel_package.rsplit('/', 1)[-1]}")

    run = Client().list_pipeline_runs(
        sort_by="asc:created",
        size=1,
        deployment_id=args.deployment_id,
        status=ExecutionStatus.INITIALIZING,
    )[0]

    logger.info("Fetching pipeline run: %s", run.id)

    def run_step_on_lightning_studio(step_name: str) -> None:
        """Run a pipeline step in a separate Lightning STUDIO.

        Args:
            step_name: Name of the step.
        """
        step_args = LightningEntrypointConfiguration.get_entrypoint_arguments(
            step_name=step_name,
            deployment_id=args.deployment_id,
            wheel_package=wheel_package_name,
        )
        entrypoint = command + step_args
        entrypoint_string = " ".join(entrypoint)
        run_command = f"{entrypoint_string}"

        step = deployment.step_configurations[step_name]
        if unique_resource_configs[step_name] != main_studio_name:
            logger.info(
                f"Creating separate studio for step: {unique_resource_configs[step_name]}"
            )
            # Get step settings
            step_settings = cast(
                LightningOrchestratorSettings,
                orchestrator.get_settings(step),
            )
            # Gather the requirements
            step_docker_settings = step.config.docker_settings
            step_requirements = gather_requirements(step_docker_settings)
            step_requirements_to_string = " ".join(
                f'"{req}"' for req in step_requirements
            )
            run_command = f"{entrypoint_string}"

            logger.info(
                f"Creating separate studio for step: {unique_resource_configs[step_name]}"
            )
            studio = Studio(name=unique_resource_configs[step_name])
            try:
                studio.start(Machine(step_settings.machine_type))
                studio.upload_file(args.wheel_package.rsplit("/", 1)[-1])
                studio.upload_file(
                    ".lightning_studio/.studiorc",
                    remote_path=".lightning_studio/.studiorc",
                )
                studio.run("pip install uv")
                studio.run(f"uv pip install {step_requirements_to_string}")
                studio.run(
                    "pip uninstall zenml -y && pip install git+https://github.com/zenml-io/zenml.git@feature/lightening-studio-orchestrator"
                )
                studio.run(
                    f"pip install {args.wheel_package.rsplit('/', 1)[-1]}"
                )
                studio.run(run_command)
            except Exception as e:
                logger.error(
                    f"Error running step {step_name} on studio {unique_resource_configs[step_name]}: {e}"
                )
                raise e
            finally:
                studio.delete()
                main_studio.delete()
        else:
            main_studio.run(run_command)

            # Pop the resource configuration for this step
        unique_resource_configs.pop(step_name)

        if main_studio_name in unique_resource_configs.values():
            # If there are more steps using this configuration, skip deprovisioning the cluster
            logger.info(
                f"Resource configuration for studio '{main_studio_name}' "
                "is used by subsequent steps. Skipping the deprovisioning of "
                "the studio."
            )
        else:
            # If there are no more steps using this configuration, down the cluster
            logger.info(
                f"Resource configuration for cluster '{main_studio_name}' "
                "is not used by subsequent steps. deprovisioning the cluster."
            )
            main_studio.delete()
        logger.info(f"Running step `{step_name}` on a Studio is completed.")

    ThreadedDagRunner(
        dag=pipeline_dag, run_fn=run_step_on_lightning_studio
    ).run()

    logger.info("Orchestration STUDIO provisioned.")


if __name__ == "__main__":
    main()
