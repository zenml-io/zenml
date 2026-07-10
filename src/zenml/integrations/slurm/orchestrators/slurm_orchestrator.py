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
"""Orchestrator that runs a whole pipeline as a graph of Slurm jobs.

Each step is submitted as its own ``sbatch`` job running the step's ZenML
Docker image on a compute node, and the pipeline DAG is reproduced with Slurm
job dependencies (``--dependency=afterok``): a step's job only starts once all
of its upstream jobs have completed successfully. Submission is fully detached
- once the jobs are queued the scheduler runs them, and each step reports its
own status back to the ZenML server, so the orchestrator does not poll.

Submission goes over SSH to a login/controller node, or via local ``sbatch``
when the client already runs on the cluster.
"""

import os
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, cast

from zenml.config.base_settings import BaseSettings
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.integrations.slurm.flavors.slurm_orchestrator_flavor import (
    SlurmOrchestratorConfig,
    SlurmOrchestratorSettings,
)
from zenml.integrations.slurm.slurm_client import (
    SlurmClient,
    build_slurm_client,
)
from zenml.integrations.slurm.slurm_job import (
    ENV_FILE,
    REQUIRED_COMPONENTS,
    build_container_command,
    build_sbatch_script,
    stage_and_submit,
    validate_remote_stack,
)
from zenml.integrations.ssh.utils import serialize_env_for_docker_env_file
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.base_orchestrator import SubmissionResult
from zenml.orchestrators.topsort import topsorted_layers
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import PipelineRunResponse, PipelineSnapshotResponse
    from zenml.stack import Stack

logger = get_logger(__name__)

ENV_ZENML_SLURM_RUN_ID = "ZENML_SLURM_ORCHESTRATOR_RUN_ID"


class SlurmOrchestrator(ContainerizedOrchestrator):
    """Orchestrator that submits a pipeline as a graph of Slurm jobs."""

    @property
    def config(self) -> SlurmOrchestratorConfig:
        """Returns the config of this orchestrator.

        Returns:
            The config.
        """
        return cast(SlurmOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[type[BaseSettings]]:
        """Settings class for this orchestrator.

        Returns:
            The settings class.
        """
        return SlurmOrchestratorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validate that the stack meets the orchestrator's requirements.

        Returns:
            A stack validator.
        """
        return StackValidator(
            required_components=REQUIRED_COMPONENTS,
            custom_validation_function=validate_remote_stack,
        )

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Returns:
            The orchestrator run id.

        Raises:
            RuntimeError: If the run id environment variable is not set, which
                means this was not called from within a step's job.
        """
        try:
            return os.environ[ENV_ZENML_SLURM_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read the orchestrator run id from environment "
                f"variable {ENV_ZENML_SLURM_RUN_ID}."
            )

    @staticmethod
    def _sorted_step_names(
        steps: Dict[str, "Step"],
    ) -> List[str]:
        """Return the step invocation ids in a topological order.

        Jobs must be submitted upstream-first so that a step's Slurm
        dependencies reference the already-submitted job ids of its parents.

        Args:
            steps: The steps keyed by invocation id.

        Returns:
            The invocation ids in a valid topological order.
        """

        def parents(name: str) -> List[str]:
            return [u for u in steps[name].spec.upstream_steps if u in steps]

        def children(name: str) -> List[str]:
            return [
                other
                for other in steps
                if name in steps[other].spec.upstream_steps
            ]

        layers = topsorted_layers(
            nodes=list(steps),
            get_node_id_fn=lambda name: name,
            get_parent_nodes=parents,
            get_child_nodes=children,
        )
        return [name for layer in layers for name in layer]

    def _job_name(self, run_id: str, step_name: str) -> str:
        """Slurm job name for a step in a run.

        Args:
            run_id: The orchestrator run id.
            step_name: The step invocation id.

        Returns:
            The Slurm job name.
        """
        return f"zenml-{run_id}-{step_name}"

    def _run_dir(self, run_id: str, step_name: str) -> str:
        """Per-step staging directory on the cluster.

        Args:
            run_id: The orchestrator run id.
            step_name: The step invocation id.

        Returns:
            The absolute path of the step's run directory.
        """
        workdir = self.config.workdir.rstrip("/")
        return f"{workdir}/{run_id}/{step_name}"

    def submit_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        base_environment: Dict[str, str],
        step_environments: Dict[str, Dict[str, str]],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submit the pipeline as a graph of dependent Slurm jobs.

        Args:
            snapshot: The pipeline snapshot to submit.
            stack: The stack the pipeline will run on.
            base_environment: Base environment shared by all steps.
            step_environments: Environment variables per step.
            placeholder_run: An optional placeholder run for the snapshot.

        Returns:
            None, since the pipeline is submitted detached.

        Raises:
            RuntimeError: If a step directory cannot be created on the cluster.
        """
        run_id = str(snapshot.id)
        # Set locally too, so get_orchestrator_run_id works if the framework
        # queries it on the submitting machine; the authoritative value is
        # injected into each step's job environment below.
        os.environ[ENV_ZENML_SLURM_RUN_ID] = run_id

        steps = snapshot.step_configurations
        client = build_slurm_client(self.config)
        submitted: Dict[str, str] = {}
        try:
            for step_name in self._sorted_step_names(steps):
                step = steps[step_name]
                job_id = self._submit_step(
                    client=client,
                    snapshot=snapshot,
                    run_id=run_id,
                    step_name=step_name,
                    step=step,
                    step_environment=step_environments[step_name],
                    upstream_job_ids=[
                        submitted[up]
                        for up in step.spec.upstream_steps
                        if up in submitted
                    ],
                )
                submitted[step_name] = job_id
                logger.info(
                    "Submitted step `%s` as Slurm job `%s`.",
                    step_name,
                    job_id,
                )
        except Exception:
            # Best-effort cleanup: cancel the jobs already queued for this run
            # so a partially-submitted pipeline does not leave work running.
            if submitted:
                client.runner.run(f"scancel {' '.join(submitted.values())}")
            raise
        finally:
            client.runner.close()

        logger.info(
            "Submitted pipeline `%s` as %d Slurm jobs.",
            snapshot.pipeline_configuration.name,
            len(submitted),
        )
        return None

    def _submit_step(
        self,
        client: SlurmClient,
        snapshot: "PipelineSnapshotResponse",
        run_id: str,
        step_name: str,
        step: "Step",
        step_environment: Dict[str, str],
        upstream_job_ids: List[str],
    ) -> str:
        """Stage and submit a single step as a Slurm job.

        Args:
            client: The Slurm client used to stage files and submit the job.
            snapshot: The pipeline snapshot.
            run_id: The orchestrator run id.
            step_name: The step invocation id.
            step: The step configuration.
            step_environment: Environment variables for the step.
            upstream_job_ids: Slurm job ids this step depends on.

        Returns:
            The submitted Slurm job id.

        Raises:
            RuntimeError: If the step directory cannot be created.
        """
        image = self.get_image(snapshot=snapshot, step_name=step_name)
        settings = cast(SlurmOrchestratorSettings, self.get_settings(step))
        run_dir = self._run_dir(run_id, step_name)
        env_file = f"{run_dir}/{ENV_FILE}"
        use_gpu = bool(step.config.resource_settings.gpu_count)

        environment = step_environment.copy()
        environment[ENV_ZENML_SLURM_RUN_ID] = run_id
        env_content = serialize_env_for_docker_env_file(environment)

        entrypoint_command = (
            StepEntrypointConfiguration.get_entrypoint_command()
            + StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name, snapshot_id=snapshot.id
            )
        )
        container_command = build_container_command(
            runtime=self.config.container_runtime,
            image=image,
            entrypoint_command=entrypoint_command,
            env_file=env_file,
            env_keys=sorted(environment),
            use_gpu=use_gpu,
            settings=settings,
        )
        script = build_sbatch_script(
            job_name=self._job_name(run_id, step_name),
            run_dir=run_dir,
            container_command=container_command,
            resources=step.config.resource_settings,
            settings=settings,
        )

        return stage_and_submit(
            client,
            run_dir=run_dir,
            env_content=env_content,
            script=script,
            dependencies=upstream_job_ids,
        )
