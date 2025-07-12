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
"""Entrypoint of the Modal orchestrator sandbox."""

import argparse
import asyncio
import os
from typing import TYPE_CHECKING, Any, Dict, cast
from uuid import UUID

import modal

from zenml.client import Client

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack
from zenml.entrypoints.pipeline_entrypoint_configuration import (
    PipelineEntrypointConfiguration,
)
from zenml.enums import ExecutionStatus
from zenml.exceptions import AuthorizationException
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalExecutionMode,
    ModalOrchestratorSettings,
)
from zenml.integrations.modal.orchestrators.modal_orchestrator import (
    ModalOrchestrator,
)
from zenml.integrations.modal.orchestrators.modal_sandbox_executor import (
    ModalSandboxExecutor,
)
from zenml.integrations.modal.utils import (
    ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID,
    setup_modal_client,
)
from zenml.logger import get_logger
from zenml.orchestrators import publish_utils
from zenml.orchestrators.dag_runner import NodeStatus, ThreadedDagRunner
from zenml.orchestrators.utils import get_config_environment_vars

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment_id", type=str, required=True)
    parser.add_argument("--orchestrator_run_id", type=str, required=True)
    parser.add_argument("--run_id", type=str, required=False)
    return parser.parse_args()


def run_step_on_modal(
    step_name: str,
    executor: ModalSandboxExecutor,
) -> None:
    """Run a pipeline step in a separate Modal sandbox.

    Args:
        step_name: Name of the step.
        executor: The Modal sandbox executor.

    Raises:
        Exception: If the sandbox fails to execute.
    """
    logger.info(f"Running step '{step_name}' in Modal sandbox")

    try:
        asyncio.run(executor.execute_step(step_name))
        logger.info(f"Step {step_name} completed successfully")
    except Exception as e:
        logger.error(f"Step {step_name} failed: {e}")
        raise


async def prepare_shared_image_cache(
    deployment: "PipelineDeploymentResponse",
    stack: "Stack",
    settings: ModalOrchestratorSettings,
) -> tuple[Dict[str, Any], Any]:
    """Pre-build all required images for pipeline steps and create shared Modal app.

    This function analyzes all steps in the deployment, identifies unique images
    needed, and pre-builds them to avoid redundant builds during step execution.

    Args:
        deployment: The pipeline deployment.
        stack: The ZenML stack.
        settings: Modal orchestrator settings.

    Returns:
        Tuple of (shared_image_cache, shared_modal_app).
    """
    from zenml.integrations.modal.orchestrators.modal_orchestrator import (
        ModalOrchestrator,
    )
    from zenml.integrations.modal.utils import get_or_build_modal_image

    logger.info("Preparing shared image cache for per-step execution")

    # Create shared Modal app
    pipeline_name = deployment.pipeline_configuration.name.replace("_", "-")
    app_name = f"zenml-pipeline-{pipeline_name}"
    shared_app = modal.App.lookup(
        app_name,
        create_if_missing=True,
        environment_name=settings.modal_environment,
    )

    image_cache: Dict[str, Any] = {}

    # Collect all unique images needed across all steps
    unique_images: Dict[str, str] = {}  # cache_key -> image_name

    # Check if deployment has a build
    if deployment.build is None:
        raise ValueError(
            "Deployment build is None, cannot prepare image cache"
        )

    # Add pipeline-level image if needed
    pipeline_image = ModalOrchestrator.get_image(deployment=deployment)
    build_id = str(deployment.build.id)
    pipeline_cache_key = (
        f"{build_id}_pipeline_{str(hash(pipeline_image))[-8:]}"
    )
    unique_images[pipeline_cache_key] = pipeline_image

    # Add step-specific images
    for step_name in deployment.step_configurations:
        step_image = ModalOrchestrator.get_image(
            deployment=deployment, step_name=step_name
        )
        image_hash = str(hash(step_image))[-8:]
        step_cache_key = f"{build_id}_{step_name}_{image_hash}"
        unique_images[step_cache_key] = step_image

    # Build all unique images
    logger.info(f"Building {len(unique_images)} unique images for pipeline")
    for cache_key, image_name in unique_images.items():
        logger.info(f"Building image: {cache_key} from {image_name}")
        try:
            built_image = get_or_build_modal_image(
                image_name=image_name,
                stack=stack,
                pipeline_name=deployment.pipeline_configuration.name,
                build_id=build_id,
                app=shared_app,
            )
            image_cache[cache_key] = built_image
            logger.info(f"Successfully cached image: {cache_key}")
        except Exception as e:
            logger.error(f"Failed to build image {cache_key}: {e}")
            raise

    logger.info(f"Image cache prepared with {len(image_cache)} images")
    return image_cache, shared_app


def execute_pipeline_mode(args: argparse.Namespace) -> None:
    """Execute entire pipeline in single sandbox mode.

    Args:
        args: Parsed command line arguments.
    """
    logger.info("Executing entire pipeline in single sandbox")
    entrypoint_args = PipelineEntrypointConfiguration.get_entrypoint_arguments(
        deployment_id=args.deployment_id
    )
    config = PipelineEntrypointConfiguration(arguments=entrypoint_args)
    config.run()


def execute_per_step_mode(
    deployment: "PipelineDeploymentResponse",
    active_stack: "Stack",
    environment: Dict[str, str],
    pipeline_settings: ModalOrchestratorSettings,
    args: argparse.Namespace,
) -> None:
    """Execute pipeline with per-step sandboxes.

    Args:
        deployment: The pipeline deployment.
        active_stack: The active ZenML stack.
        environment: Environment variables.
        pipeline_settings: Modal orchestrator settings.
        args: Parsed command line arguments.
    """
    logger.info("Executing pipeline with per-step sandboxes")

    # Prepare shared image cache and Modal app for all steps
    logger.info("Pre-building images for step execution")
    shared_image_cache, shared_app = asyncio.run(
        prepare_shared_image_cache(
            deployment=deployment,
            stack=active_stack,
            settings=pipeline_settings,
        )
    )

    # Create shared executor instance that will be reused across steps
    shared_executor = ModalSandboxExecutor(
        deployment=deployment,
        stack=active_stack,
        environment=environment,
        settings=pipeline_settings,
        shared_image_cache=shared_image_cache,
        shared_app=shared_app,
    )

    def run_step_wrapper(step_name: str) -> None:
        """Wrapper to execute step with shared resources."""
        run_step_on_modal(step_name, shared_executor)

    def finalize_wrapper(node_states: Dict[str, NodeStatus]) -> None:
        """Wrapper to finalize pipeline execution."""
        finalize_run(node_states, args)

    # Build DAG from deployment
    pipeline_dag = {
        step_name: step.spec.upstream_steps
        for step_name, step in deployment.step_configurations.items()
    }

    logger.info(f"Executing {len(pipeline_dag)} steps with shared image cache")

    # Run using ThreadedDagRunner with optimized execution
    ThreadedDagRunner(
        dag=pipeline_dag,
        run_fn=run_step_wrapper,
        finalize_fn=finalize_wrapper,
        max_parallelism=getattr(pipeline_settings, "max_parallelism", None),
    ).run()


def finalize_run(
    node_states: Dict[str, NodeStatus], args: argparse.Namespace
) -> None:
    """Finalize the run by updating step and pipeline run statuses.

    Args:
        node_states: The states of the nodes.
        args: Parsed command line arguments.
    """
    try:
        client = Client()
        deployment = client.get_deployment(args.deployment_id)

        # Fetch the pipeline run
        list_args: Dict[str, Any] = {}
        if args.run_id:
            list_args = dict(id=UUID(args.run_id))
        else:
            list_args = dict(orchestrator_run_id=args.orchestrator_run_id)

        pipeline_runs = client.list_pipeline_runs(
            hydrate=True,
            project=deployment.project_id,
            deployment_id=deployment.id,
            **list_args,
        )

        if not len(pipeline_runs):
            return

        pipeline_run = pipeline_runs[0]
        pipeline_failed = False

        for step_name, node_state in node_states.items():
            if node_state != NodeStatus.FAILED:
                continue

            pipeline_failed = True

            # Mark failed step runs as failed
            step_run = pipeline_run.steps.get(step_name)
            if step_run and step_run.status in {
                ExecutionStatus.INITIALIZING,
                ExecutionStatus.RUNNING,
            }:
                publish_utils.publish_failed_step_run(step_run.id)

        # Mark pipeline as failed if any steps failed
        if pipeline_failed and pipeline_run.status in {
            ExecutionStatus.INITIALIZING,
            ExecutionStatus.RUNNING,
        }:
            publish_utils.publish_failed_pipeline_run(pipeline_run.id)

    except AuthorizationException:
        # Token may be invalidated after completion, this is expected
        pass


def main() -> None:
    """Entrypoint of the Modal orchestrator sandbox.

    This entrypoint is used to execute the pipeline in a Modal sandbox.

    Raises:
        Exception: If the pipeline execution fails.
    """
    logger.info("Modal orchestrator sandbox started.")

    args = parse_args()
    os.environ[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID] = args.orchestrator_run_id

    client = Client()
    active_stack = client.active_stack
    orchestrator = active_stack.orchestrator
    assert isinstance(orchestrator, ModalOrchestrator)

    deployment = client.get_deployment(args.deployment_id)
    pipeline_settings = cast(
        ModalOrchestratorSettings,
        orchestrator.get_settings(deployment),
    )

    # Setup Modal client
    setup_modal_client(
        token_id=orchestrator.config.token_id,
        token_secret=orchestrator.config.token_secret,
        workspace=orchestrator.config.workspace,
        environment=orchestrator.config.modal_environment,
    )

    environment = get_config_environment_vars()
    environment[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID] = args.orchestrator_run_id

    # Check execution mode
    execution_mode = getattr(
        pipeline_settings, "execution_mode", ModalExecutionMode.PIPELINE
    )

    try:
        # Execute pipeline based on execution mode
        if execution_mode == ModalExecutionMode.PIPELINE:
            execute_pipeline_mode(args)
        else:
            execute_per_step_mode(
                deployment, active_stack, environment, pipeline_settings, args
            )

        logger.info("Pipeline execution completed successfully")

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
