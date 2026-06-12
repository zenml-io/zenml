#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Implementation of the Cloudflare orchestrator (proof of concept).

Runs every pipeline step in its own Cloudflare Sandbox, dispatched through
the Cloudflare sandbox stack component (and therefore through the bridge
Worker it is configured with). The orchestration loop itself runs on the
client, mirroring the local Docker orchestrator — Cloudflare Workflows are
the natural home for it later.
"""

import os
import time
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)
from uuid import uuid4

from zenml.config.base_settings import BaseSettings
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import ExecutionMode, StackComponentType
from zenml.integrations.cloudflare.flavors.cloudflare_orchestrator_flavor import (
    CloudflareOrchestratorConfig,
    CloudflareOrchestratorSettings,
)
from zenml.integrations.cloudflare.flavors.cloudflare_sandbox_flavor import (
    CloudflareSandboxSettings,
)
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator, SubmissionResult
from zenml.stack import Stack, StackValidator
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.models import (
        PipelineRunResponse,
        PipelineSnapshotResponse,
    )
    from zenml.sandboxes.session import SandboxSession

logger = get_logger(__name__)

ENV_ZENML_CLOUDFLARE_ORCHESTRATOR_RUN_ID = (
    "ZENML_CLOUDFLARE_ORCHESTRATOR_RUN_ID"
)

CLOUDFLARE_SANDBOX_FLAVOR_NAME = "cloudflare"


class CloudflareOrchestrator(BaseOrchestrator):
    """Orchestrator that runs each step in a Cloudflare Sandbox."""

    @property
    def config(self) -> CloudflareOrchestratorConfig:
        """Returns the orchestrator config.

        Returns:
            The configuration.
        """
        return cast(CloudflareOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Cloudflare orchestrator.

        Returns:
            The settings class.
        """
        return CloudflareOrchestratorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures the stack contains a Cloudflare sandbox to dispatch to.

        Returns:
            A `StackValidator` instance.
        """

        def _ensure_cloudflare_sandbox(stack: "Stack") -> Tuple[bool, str]:
            sandbox = stack.sandbox
            if (
                sandbox is None
                or sandbox.flavor != CLOUDFLARE_SANDBOX_FLAVOR_NAME
            ):
                return False, (
                    "The Cloudflare orchestrator launches steps through a "
                    "Cloudflare sandbox component and requires one in the "
                    "same stack: `zenml stack update --sandbox "
                    "<CLOUDFLARE_SANDBOX_NAME>`."
                )
            return True, ""

        return StackValidator(
            required_components={StackComponentType.SANDBOX},
            custom_validation_function=_ensure_cloudflare_sandbox,
        )

    def get_orchestrator_run_id(self) -> str:
        """Returns the run id of the active orchestrator run.

        Returns:
            The orchestrator run id.

        Raises:
            RuntimeError: If the run id cannot be read from the environment.
        """
        try:
            return os.environ[ENV_ZENML_CLOUDFLARE_ORCHESTRATOR_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_CLOUDFLARE_ORCHESTRATOR_RUN_ID}."
            )

    @property
    def supported_execution_modes(self) -> List[ExecutionMode]:
        """Supported execution modes for this orchestrator.

        Returns:
            Supported execution modes for this orchestrator.
        """
        return [
            ExecutionMode.FAIL_FAST,
            ExecutionMode.STOP_ON_FAILURE,
            ExecutionMode.CONTINUE_ON_FAILURE,
        ]

    def _run_in_sandbox(
        self,
        session: "SandboxSession",
        argv: List[str],
        description: str,
    ) -> int:
        """Runs a command in a sandbox session, streaming output to the logs.

        Args:
            session: The sandbox session to exec in.
            argv: The command to run.
            description: Human-readable description used in log lines.

        Returns:
            The command's exit code.
        """
        process = session.exec(argv)
        for line in process.stdout():
            logger.info("[%s] %s", description, line.rstrip("\n"))
        exit_code = process.wait()
        if exit_code != 0:
            for line in process.stderr():
                logger.error("[%s] %s", description, line.rstrip("\n"))
        return exit_code

    def submit_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        base_environment: Dict[str, str],
        step_environments: Dict[str, Dict[str, str]],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Runs each pipeline step in its own Cloudflare Sandbox.

        Args:
            snapshot: The pipeline snapshot to submit.
            stack: The stack the pipeline will run on.
            base_environment: Base environment shared by all steps.
            step_environments: Environment variables to set when executing
                specific steps.
            placeholder_run: An optional placeholder run for the snapshot.

        Raises:
            RuntimeError: If the pipeline run fails.

        Returns:
            Optional submission result.
        """
        if snapshot.schedule:
            logger.warning(
                "The Cloudflare orchestrator does not support schedules. "
                "The schedule will be ignored and the pipeline run "
                "immediately."
            )

        sandbox = stack.sandbox
        assert sandbox is not None  # guaranteed by the stack validator

        orchestrator_run_id = str(uuid4())
        start_time = time.time()
        execution_mode = snapshot.pipeline_configuration.execution_mode

        failed_steps: List[str] = []
        skipped_steps: List[str] = []

        for step_name, step in snapshot.step_configurations.items():
            if (
                execution_mode == ExecutionMode.STOP_ON_FAILURE
                and failed_steps
            ):
                logger.warning(
                    "Skipping step %s due to the failed step(s): %s "
                    "(Execution mode %s)",
                    step_name,
                    ", ".join(failed_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if failed_upstream_steps := [
                fs for fs in failed_steps if fs in step.spec.upstream_steps
            ]:
                logger.warning(
                    "Skipping step %s due to failure in upstream step(s): "
                    "%s (Execution mode %s)",
                    step_name,
                    ", ".join(failed_upstream_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if skipped_upstream_steps := [
                fs for fs in skipped_steps if fs in step.spec.upstream_steps
            ]:
                logger.warning(
                    "Skipping step %s due to the skipped upstream step(s) "
                    "%s (Execution mode %s)",
                    step_name,
                    ", ".join(skipped_upstream_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Cloudflare sandboxes do not expose resource knobs "
                    "(CPU/memory/GPU); ignoring the resource configuration "
                    "for step %s.",
                    step_name,
                )

            settings = cast(
                CloudflareOrchestratorSettings, self.get_settings(step)
            )

            step_environment = dict(step_environments[step_name])
            step_environment[ENV_ZENML_CLOUDFLARE_ORCHESTRATOR_RUN_ID] = (
                orchestrator_run_id
            )

            entrypoint_args = (
                StepEntrypointConfiguration.get_entrypoint_arguments(
                    step_name=step_name, snapshot_id=snapshot.id
                )
            )
            # The sandbox image ships `python3` only, so the first element
            # of the generic entrypoint command ("python") is replaced.
            entrypoint_argv = [
                "python3",
                *StepEntrypointConfiguration.get_entrypoint_command()[1:],
                *entrypoint_args,
            ]

            logger.info(
                "Running step `%s` in a Cloudflare sandbox:", step_name
            )
            sandbox_settings = CloudflareSandboxSettings(
                sandbox_environment=step_environment,
                timeout_ms=settings.step_timeout_ms,
            )
            session = sandbox.create_session(settings=sandbox_settings)
            try:
                exit_code = self._run_in_sandbox(
                    session,
                    [
                        "pip3",
                        "install",
                        "--quiet",
                        settings.zenml_requirement,
                    ],
                    description=f"{step_name}:bootstrap",
                )
                if exit_code == 0:
                    exit_code = self._run_in_sandbox(
                        session,
                        entrypoint_argv,
                        description=step_name,
                    )
            finally:
                session.destroy()

            if exit_code != 0:
                failed_steps.append(step_name)
                error_message = (
                    f"Step `{step_name}` failed in the Cloudflare sandbox "
                    f"with exit code {exit_code}."
                )
                if execution_mode == ExecutionMode.FAIL_FAST:
                    raise RuntimeError(error_message)
                logger.error(error_message)

        if failed_steps:
            raise RuntimeError(
                "Pipeline run has failed due to failure in step(s): "
                f"{', '.join(failed_steps)}"
            )

        run_duration = time.time() - start_time
        logger.info(
            "Pipeline run has finished in `%s`.",
            string_utils.get_human_readable_time(run_duration),
        )
        return None
