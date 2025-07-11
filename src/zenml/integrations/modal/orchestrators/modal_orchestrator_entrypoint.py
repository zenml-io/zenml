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
from typing import Any, Dict, Optional, cast
from uuid import UUID

from zenml.client import Client
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
        if execution_mode == ModalExecutionMode.PIPELINE:
            # Execute entire pipeline in this sandbox
            logger.info("Executing entire pipeline in single sandbox")
            entrypoint_args = (
                PipelineEntrypointConfiguration.get_entrypoint_arguments(
                    deployment_id=args.deployment_id
                )
            )
            config = PipelineEntrypointConfiguration(arguments=entrypoint_args)
            config.run()

        else:
            # PER_STEP mode: Execute each step in separate sandbox
            logger.info("Executing pipeline with per-step sandboxes")

            # Create executor for step execution
            executor = ModalSandboxExecutor(
                deployment=deployment,
                stack=active_stack,
                environment=environment,
                settings=pipeline_settings,
            )

            def run_step_wrapper(step_name: str) -> None:
                run_step_on_modal(step_name, executor)

            def finalize_wrapper(node_states: Dict[str, NodeStatus]) -> None:
                finalize_run(node_states, args)

            # Build DAG from deployment
            pipeline_dag = {
                step_name: step.spec.upstream_steps
                for step_name, step in deployment.step_configurations.items()
            }

            # Run using ThreadedDagRunner
            ThreadedDagRunner(
                dag=pipeline_dag,
                run_fn=run_step_wrapper,
                finalize_fn=finalize_wrapper,
                max_parallelism=getattr(
                    pipeline_settings, "max_parallelism", None
                ),
            ).run()

        logger.info("Pipeline execution completed successfully")

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
