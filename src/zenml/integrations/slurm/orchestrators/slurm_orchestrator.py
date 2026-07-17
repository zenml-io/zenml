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

Dynamic pipelines run as a single Slurm orchestration job sized via the
pipeline-level resource settings; their steps execute inline inside that
job's allocation. Submitting per-step jobs from within an active Slurm job
would deadlock under per-user job limits and waste the parent allocation
while children wait in the queue, so the orchestrator deliberately does not
support isolated steps.
"""

import os
import shlex
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    cast,
)

from zenml.config.base_settings import BaseSettings
from zenml.config.resource_settings import ResourceSettings
from zenml.constants import METADATA_ORCHESTRATOR_RUN_ID
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.enums import ExecutionMode, ExecutionStatus
from zenml.integrations.slurm.flavors.slurm_orchestrator_flavor import (
    SlurmOrchestratorConfig,
    SlurmOrchestratorSettings,
)
from zenml.integrations.slurm.slurm_client import (
    PENDING_STATES,
    RUNNING_STATES,
    SlurmClient,
    build_slurm_client,
)
from zenml.integrations.slurm.slurm_job import (
    CANCELLED_FILE,
    DOCKER_CONFIG_DIR,
    ENROOT_CONFIG_DIR,
    ENV_FILE,
    EXIT_CODE_FILE,
    OUTPUT_FILE,
    REGISTRY_AUTH_FILE,
    REQUIRED_COMPONENTS,
    SCRIPT_FILE,
    build_container_command,
    build_registry_auth,
    build_sbatch_script,
    serialize_environment,
    stage_and_submit,
    validate_remote_stack,
)
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator, SubmissionResult
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import (
        PipelineRunResponse,
        PipelineSnapshotResponse,
    )
    from zenml.stack import Stack

logger = get_logger(__name__)

ENV_ZENML_SLURM_RUN_ID = "ZENML_SLURM_ORCHESTRATOR_RUN_ID"
SLURM_JOB_IDS_METADATA_KEY = "slurm_job_ids"
SLURM_CLEANUP_JOB_ID_METADATA_KEY = "slurm_cleanup_job_id"
SLURM_ORCHESTRATION_JOB_ID_METADATA_KEY = "slurm_orchestration_job_id"
_CLEANUP_COMPLETE_FILE = "cleanup_complete"


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
    def supported_execution_modes(self) -> List[ExecutionMode]:
        """Execution modes supported by this orchestrator.

        Returns:
            The supported execution modes.
        """
        return [
            ExecutionMode.FAIL_FAST,
            ExecutionMode.STOP_ON_FAILURE,
            ExecutionMode.CONTINUE_ON_FAILURE,
        ]

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

    def _orchestration_run_dir(self, run_id: str) -> str:
        """Staging directory for a dynamic orchestration job.

        Args:
            run_id: The orchestrator run id.

        Returns:
            The absolute path of the orchestration job's run directory.
        """
        workdir = self.config.workdir.rstrip("/")
        return f"{workdir}/{run_id}/orchestration"

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
            base_environment: Base environment shared by all steps. Unused: the
                per-step environments already include it.
            step_environments: Environment variables per step.
            placeholder_run: The placeholder run for the pipeline.

        Returns:
            None, since the pipeline is submitted detached.

        Raises:
            RuntimeError: If the pipeline has a schedule, which is not
                supported.
            Exception: Re-raised after cancelling already-queued jobs if a
                step fails to submit.
        """
        if snapshot.schedule:
            raise RuntimeError(
                "The Slurm orchestrator does not support scheduled pipelines. "
                "Remove the schedule and trigger the pipeline directly (e.g. "
                "from your own cron job or CI), or use an orchestrator that "
                "supports scheduling."
            )
        # The run id must be unique per run and identical for every step of the
        # run; the placeholder run id satisfies both (the snapshot id does not -
        # a snapshot can be executed many times). It is injected into each
        # step's job environment below and read back by
        # `get_orchestrator_run_id` inside the step's job.
        assert placeholder_run is not None
        run_id = str(placeholder_run.id)

        steps = snapshot.step_configurations
        client = build_slurm_client(self.config)
        submitted: Dict[str, str] = {}
        sensitive_paths: List[str] = []
        cleanup_job_id: Optional[str] = None
        cleanup_settings = cast(
            SlurmOrchestratorSettings, self.get_settings(snapshot)
        )
        container_registry = stack.container_registry
        assert container_registry is not None
        try:
            # `step_configurations` is topologically sorted by contract, so
            # every step's upstream job ids are already submitted when its
            # `--dependency=afterok` list is built.
            for step_name, step in steps.items():
                job_id, step_sensitive_paths = self._submit_step(
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
                    registry_uri=container_registry.config.uri,
                    registry_credentials=container_registry.credentials,
                )
                submitted[step_name] = job_id
                sensitive_paths.extend(step_sensitive_paths)
                logger.info(
                    "Submitted step `%s` as Slurm job `%s`.",
                    step_name,
                    job_id,
                )
            cleanup_job_id = self._submit_cleanup_job(
                client=client,
                run_id=run_id,
                submitted=submitted,
                sensitive_paths=sensitive_paths,
                settings=cleanup_settings,
            )
        except Exception:
            # Best-effort cleanup: cancel the jobs already queued for this run
            # so a partially-submitted pipeline does not leave work running.
            if submitted:
                for job_id in submitted.values():
                    try:
                        client.cancel(job_id)
                    except Exception:
                        logger.warning(
                            "Failed to cancel Slurm job `%s` after a submission "
                            "failure.",
                            job_id,
                        )
                if sensitive_paths:
                    client.runner.run(
                        "rm -rf -- "
                        + " ".join(
                            shlex.quote(path) for path in sensitive_paths
                        )
                    )
            raise
        finally:
            client.runner.close()

        logger.info(
            "Submitted pipeline `%s` as %d Slurm jobs.",
            snapshot.pipeline_configuration.name,
            len(submitted),
        )
        assert cleanup_job_id is not None
        return SubmissionResult(
            metadata={
                METADATA_ORCHESTRATOR_RUN_ID: run_id,
                SLURM_JOB_IDS_METADATA_KEY: submitted,
                SLURM_CLEANUP_JOB_ID_METADATA_KEY: cleanup_job_id,
            }
        )

    def submit_dynamic_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submit a dynamic pipeline as a Slurm orchestration job.

        Args:
            snapshot: The pipeline snapshot to submit.
            stack: The stack the pipeline will run on.
            environment: Environment variables for the orchestration
                environment.
            placeholder_run: The placeholder run for the pipeline.

        Returns:
            Submission metadata containing the orchestration job id.

        Raises:
            RuntimeError: If the pipeline has a schedule, which is not
                supported.
        """
        from zenml.pipelines.dynamic.entrypoint_configuration import (
            DynamicPipelineEntrypointConfiguration,
        )

        if snapshot.schedule:
            raise RuntimeError(
                "The Slurm orchestrator does not support scheduled pipelines. "
                "Remove the schedule and trigger the pipeline directly (e.g. "
                "from your own cron job or CI), or use an orchestrator that "
                "supports scheduling."
            )

        assert placeholder_run is not None
        run_id = str(placeholder_run.id)
        settings = cast(SlurmOrchestratorSettings, self.get_settings(snapshot))
        container_registry = stack.container_registry
        assert container_registry is not None
        command = (
            DynamicPipelineEntrypointConfiguration.get_entrypoint_command()
            + DynamicPipelineEntrypointConfiguration.get_entrypoint_arguments(
                snapshot_id=snapshot.id,
                run_id=run_id,
            )
        )

        client = build_slurm_client(self.config)
        try:
            job_id, sensitive_paths = self._submit_container_job(
                client=client,
                run_id=run_id,
                run_dir=self._orchestration_run_dir(run_id),
                job_name=f"zenml-{run_id}-orchestration",
                image=self.get_image(snapshot=snapshot),
                entrypoint_command=command,
                environment=environment,
                # Every step of a dynamic pipeline runs inline inside this
                # job, so its allocation must carry the pipeline's resources.
                resources=snapshot.pipeline_configuration.resource_settings,
                settings=settings,
                registry_uri=container_registry.config.uri,
                registry_credentials=container_registry.credentials,
            )
            try:
                # The job's own EXIT trap scrubs credentials on clean exits,
                # but a hard kill (NODE_FAIL, OOM) never runs it - the
                # `afterany` cleanup job is the reaper of last resort, same
                # as for static runs. Its completion marker also makes a
                # missing exit sentinel conclusive during reconciliation.
                cleanup_job_id = self._submit_cleanup_job(
                    client=client,
                    run_id=run_id,
                    submitted={"orchestration": job_id},
                    sensitive_paths=sensitive_paths,
                    settings=settings,
                )
            except Exception:
                # Without the reaper, a hard-killed job would strand
                # credentials on the shared filesystem indefinitely - refuse
                # to run in that state.
                try:
                    client.cancel(job_id)
                except Exception:
                    logger.warning(
                        "Failed to cancel Slurm orchestration job `%s` "
                        "after its cleanup job could not be submitted.",
                        job_id,
                    )
                if sensitive_paths:
                    client.runner.run(
                        "rm -rf -- "
                        + " ".join(
                            shlex.quote(path) for path in sensitive_paths
                        )
                    )
                raise
        finally:
            client.runner.close()

        logger.info(
            "Submitted dynamic pipeline `%s` as Slurm orchestration job `%s`.",
            snapshot.pipeline_configuration.name,
            job_id,
        )
        return SubmissionResult(
            metadata={
                METADATA_ORCHESTRATOR_RUN_ID: run_id,
                SLURM_ORCHESTRATION_JOB_ID_METADATA_KEY: job_id,
                SLURM_CLEANUP_JOB_ID_METADATA_KEY: cleanup_job_id,
            }
        )

    def _submit_container_job(
        self,
        client: SlurmClient,
        run_id: str,
        run_dir: str,
        job_name: str,
        image: str,
        entrypoint_command: List[str],
        environment: Dict[str, str],
        resources: ResourceSettings,
        settings: SlurmOrchestratorSettings,
        registry_uri: Optional[str],
        registry_credentials: Optional[Tuple[str, str]],
        dependencies: Optional[List[str]] = None,
    ) -> Tuple[str, List[str]]:
        """Stage and submit one containerized Slurm job.

        Args:
            client: The Slurm client used to stage files and submit the job.
            run_id: The orchestrator run id to inject into the job
                environment.
            run_dir: Per-job staging directory.
            job_name: Slurm job name.
            image: Container image to execute.
            entrypoint_command: Full command executed inside the container.
            environment: Runtime environment for the job.
            resources: Resource requests for the Slurm job.
            settings: Slurm settings for the job.
            registry_uri: URI of the stack's container registry.
            registry_credentials: Registry username and password.
            dependencies: Optional Slurm job ids this job depends on.

        Returns:
            The submitted Slurm job id and credential-bearing paths.
        """
        env_file = f"{run_dir}/{ENV_FILE}"
        runtime_environment = environment.copy()
        runtime_environment[ENV_ZENML_SLURM_RUN_ID] = run_id
        env_content = serialize_environment(
            runtime_environment, runtime=self.config.container_runtime
        )
        registry_auth = build_registry_auth(
            runtime=self.config.container_runtime,
            run_dir=run_dir,
            registry_uri=registry_uri,
            credentials=registry_credentials,
        )
        container_command = build_container_command(
            runtime=self.config.container_runtime,
            image=image,
            entrypoint_command=entrypoint_command,
            env_file=env_file,
            env_keys=sorted(runtime_environment),
            use_gpu=bool(resources.gpu_count),
            settings=settings,
            registry_auth=registry_auth,
        )
        script = build_sbatch_script(
            job_name=job_name,
            run_dir=run_dir,
            container_command=container_command,
            resources=resources,
            settings=settings,
            sensitive_paths=registry_auth.sensitive_paths,
        )
        job_id = stage_and_submit(
            client,
            run_dir=run_dir,
            env_content=env_content,
            script=script,
            dependencies=dependencies,
            extra_files=registry_auth.files,
        )
        return job_id, [env_file, *registry_auth.sensitive_paths]

    def _submit_step(
        self,
        client: SlurmClient,
        snapshot: "PipelineSnapshotResponse",
        run_id: str,
        step_name: str,
        step: "Step",
        step_environment: Dict[str, str],
        upstream_job_ids: List[str],
        registry_uri: Optional[str],
        registry_credentials: Optional[Tuple[str, str]],
    ) -> Tuple[str, List[str]]:
        """Stage and submit a single step as a Slurm job.

        Args:
            client: The Slurm client used to stage files and submit the job.
            snapshot: The pipeline snapshot.
            run_id: The orchestrator run id.
            step_name: The step invocation id.
            step: The step configuration.
            step_environment: Environment variables for the step.
            upstream_job_ids: Slurm job ids this step depends on.
            registry_uri: URI of the stack's container registry.
            registry_credentials: Registry username and password.

        Returns:
            The submitted Slurm job id and credential-bearing paths.
        """
        settings = cast(SlurmOrchestratorSettings, self.get_settings(step))
        entrypoint_command = (
            StepEntrypointConfiguration.get_entrypoint_command()
            + StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name, snapshot_id=snapshot.id
            )
        )
        return self._submit_container_job(
            client=client,
            run_id=run_id,
            run_dir=self._run_dir(run_id, step_name),
            job_name=self._job_name(run_id, step_name),
            image=self.get_image(snapshot=snapshot, step_name=step_name),
            entrypoint_command=entrypoint_command,
            environment=step_environment,
            resources=step.config.resource_settings,
            settings=settings,
            registry_uri=registry_uri,
            registry_credentials=registry_credentials,
            dependencies=upstream_job_ids,
        )

    def _submit_cleanup_job(
        self,
        client: SlurmClient,
        run_id: str,
        submitted: Dict[str, str],
        sensitive_paths: List[str],
        settings: SlurmOrchestratorSettings,
    ) -> str:
        """Submit one credential cleanup job after all DAG jobs terminate.

        Args:
            client: Slurm client used for submission.
            run_id: Orchestrator run ID.
            submitted: Mapping of step names to Slurm job IDs.
            sensitive_paths: Credential-bearing files and directories.
            settings: Pipeline-level Slurm settings for the cleanup job.

        Returns:
            The cleanup Slurm job ID.

        Raises:
            RuntimeError: If the cleanup job cannot be staged.
        """
        job_ids = list(submitted.values())
        cleanup_dir = f"{self.config.workdir.rstrip('/')}/{run_id}/cleanup"
        cleanup_marker = f"{cleanup_dir}/{_CLEANUP_COMPLETE_FILE}"
        cleanup_command = "rm -rf -- " + " ".join(
            shlex.quote(path) for path in sensitive_paths
        )
        directives = [
            f"#SBATCH --job-name=zenml-{run_id}-cleanup",
            f"#SBATCH --output={cleanup_dir}/{OUTPUT_FILE}",
        ]
        if settings.partition:
            directives.append(f"#SBATCH --partition={settings.partition}")
        if settings.account:
            directives.append(f"#SBATCH --account={settings.account}")
        if settings.qos:
            directives.append(f"#SBATCH --qos={settings.qos}")
        for directive in settings.extra_sbatch_directives:
            directives.append(f"#SBATCH {directive}")

        script = f"""#!/bin/bash
{chr(10).join(directives)}

set -eo pipefail
{cleanup_command}
touch {shlex.quote(cleanup_marker)}
"""
        result = client.runner.run(
            f"umask 077 && mkdir -p {shlex.quote(cleanup_dir)} && "
            f"chmod 700 {shlex.quote(cleanup_dir)}"
        )
        if result.exit_code != 0:
            raise RuntimeError(
                f"Failed to create cleanup directory `{cleanup_dir}`: "
                f"{result.stderr.strip()}"
            )
        script_path = f"{cleanup_dir}/{SCRIPT_FILE}"
        client.runner.put_text(script_path, script, mode=0o700)
        return client.submit(
            script_path,
            dependencies=job_ids,
            dependency_type="afterany",
        )

    def fetch_status(
        self, run: "PipelineRunResponse", include_steps: bool = False
    ) -> Tuple[
        Optional[ExecutionStatus], Optional[Dict[str, ExecutionStatus]]
    ]:
        """Reconcile a detached pipeline run with its Slurm jobs.

        Args:
            run: Pipeline run submitted by this orchestrator.
            include_steps: Whether to return individual step statuses.

        Returns:
            The pipeline status and optional step statuses.
        """
        raw_job_ids = run.run_metadata.get(SLURM_JOB_IDS_METADATA_KEY)
        if not isinstance(raw_job_ids, dict):
            return self._fetch_dynamic_status(run)

        job_ids = {
            str(name): str(job_id) for name, job_id in raw_job_ids.items()
        }
        cleanup_marker = (
            f"{self.config.workdir.rstrip('/')}/{run.id}/cleanup/"
            f"{_CLEANUP_COMPLETE_FILE}"
        )
        client = build_slurm_client(self.config)
        try:
            try:
                client.runner.read_text(cleanup_marker)
            except Exception:
                cleanup_complete = False
            else:
                cleanup_complete = True

            job_states = client.get_job_states(list(job_ids.values()))
            statuses = {
                step_name: self._get_job_status(
                    client=client,
                    state=job_states[job_id],
                    run_dir=self._run_dir(str(run.id), step_name),
                    cleanup_complete=cleanup_complete,
                )
                for step_name, job_id in job_ids.items()
            }

            known_statuses = [status for status in statuses.values() if status]
            pipeline_status: Optional[ExecutionStatus] = None
            if not run.status.is_finished:
                failed_or_cancelled = any(
                    status
                    in {ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}
                    for status in known_statuses
                )
                all_terminal = len(known_statuses) == len(statuses) and all(
                    status.is_finished for status in known_statuses
                )
                if failed_or_cancelled:
                    if self._should_cancel_unfinished_jobs(run):
                        pipeline_status = ExecutionStatus.FAILED
                        self._cancel_unfinished_jobs(
                            client=client,
                            run_id=str(run.id),
                            job_ids=job_ids,
                            statuses=statuses,
                        )
                    elif all_terminal:
                        pipeline_status = ExecutionStatus.FAILED
                    elif ExecutionStatus.RUNNING in known_statuses:
                        pipeline_status = ExecutionStatus.RUNNING
                    else:
                        pipeline_status = ExecutionStatus.PROVISIONING
                elif len(known_statuses) == len(statuses) and all(
                    status == ExecutionStatus.COMPLETED
                    for status in known_statuses
                ):
                    pipeline_status = ExecutionStatus.COMPLETED
                elif ExecutionStatus.RUNNING in known_statuses:
                    pipeline_status = ExecutionStatus.RUNNING
                elif known_statuses:
                    pipeline_status = ExecutionStatus.PROVISIONING
        finally:
            client.runner.close()

        step_statuses = None
        if include_steps:
            step_statuses = {
                name: status for name, status in statuses.items() if status
            }
        return pipeline_status, step_statuses

    @staticmethod
    def _should_cancel_unfinished_jobs(run: "PipelineRunResponse") -> bool:
        """Check whether failure reconciliation should cancel sibling jobs.

        Args:
            run: Pipeline run submitted by this orchestrator.

        Returns:
            Whether unfinished jobs should be cancelled.
        """
        return run.config.execution_mode in {
            ExecutionMode.FAIL_FAST,
            ExecutionMode.STOP_ON_FAILURE,
        }

    def _fetch_dynamic_status(
        self, run: "PipelineRunResponse"
    ) -> Tuple[Optional[ExecutionStatus], None]:
        """Reconcile a dynamic pipeline run with its orchestration job.

        Args:
            run: Pipeline run submitted by this orchestrator.

        Returns:
            The pipeline status and no step statuses.
        """
        job_id = run.run_metadata.get(SLURM_ORCHESTRATION_JOB_ID_METADATA_KEY)
        if job_id is None:
            logger.warning("No Slurm job metadata found for run `%s`.", run.id)
            return None, None

        cleanup_marker = (
            f"{self.config.workdir.rstrip('/')}/{run.id}/cleanup/"
            f"{_CLEANUP_COMPLETE_FILE}"
        )
        client = build_slurm_client(self.config)
        try:
            try:
                client.runner.read_text(cleanup_marker)
            except Exception:
                cleanup_complete = False
            else:
                cleanup_complete = True

            state = client.get_job_state(str(job_id))
            status = self._get_job_status(
                client=client,
                state=state,
                run_dir=self._orchestration_run_dir(str(run.id)),
                # The orchestration job writes its own exit-code sentinel
                # via its EXIT trap; the `afterany` cleanup job's marker
                # tells us when there is nothing left to wait for. Until
                # then, a job that has vanished from the queue with no
                # sentinel is unknown, not failed - mirroring the static
                # DAG reconciliation. Declaring FAILED on first sight would
                # terminally mislabel a run whose sentinel merely lags the
                # queue purge (NFS/Lustre flush).
                cleanup_complete=cleanup_complete,
            )
            if status is None and state is None:
                logger.warning(
                    "Slurm orchestration job `%s` for run `%s` is no longer "
                    "known to Slurm and has not written an exit-code "
                    "sentinel yet; keeping the run status unchanged until "
                    "the cleanup job resolves it.",
                    job_id,
                    run.id,
                )
        finally:
            client.runner.close()

        pipeline_status: Optional[ExecutionStatus] = None
        if not run.status.is_finished and status:
            if status in {ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}:
                pipeline_status = ExecutionStatus.FAILED
            elif status == ExecutionStatus.COMPLETED:
                pipeline_status = ExecutionStatus.COMPLETED
            elif status == ExecutionStatus.RUNNING:
                pipeline_status = ExecutionStatus.RUNNING
            elif status == ExecutionStatus.QUEUED:
                pipeline_status = ExecutionStatus.PROVISIONING

        return pipeline_status, None

    @staticmethod
    def _get_job_status(
        client: SlurmClient,
        state: Optional[str],
        run_dir: str,
        cleanup_complete: bool,
    ) -> Optional[ExecutionStatus]:
        """Map one Slurm job and its sentinel to a ZenML status.

        Args:
            client: Slurm client used to inspect the job.
            state: Slurm job state fetched for the job.
            run_dir: Per-step staging directory.
            cleanup_complete: Whether the final cleanup job has run.

        Returns:
            The reconciled status, or None while the outcome is unknown.
        """
        if state in PENDING_STATES:
            return ExecutionStatus.QUEUED
        if state in RUNNING_STATES:
            return ExecutionStatus.RUNNING
        if state == "COMPLETED":
            return ExecutionStatus.COMPLETED
        if state is not None:
            if state.startswith("CANCEL"):
                return ExecutionStatus.CANCELLED
            return ExecutionStatus.FAILED

        try:
            client.runner.read_text(f"{run_dir}/{CANCELLED_FILE}")
        except Exception:
            pass
        else:
            return ExecutionStatus.CANCELLED

        try:
            exit_code = client.runner.read_text(
                f"{run_dir}/{EXIT_CODE_FILE}"
            ).strip()
        except Exception:
            return ExecutionStatus.FAILED if cleanup_complete else None
        return (
            ExecutionStatus.COMPLETED
            if exit_code == "0"
            else ExecutionStatus.FAILED
        )

    def _stop_run(
        self, run: "PipelineRunResponse", graceful: bool = False
    ) -> None:
        """Cancel all Slurm jobs submitted for a pipeline run.

        Args:
            run: Pipeline run submitted by this orchestrator.
            graceful: Unused. Slurm does not expose a DAG-level graceful stop,
                so both graceful and forceful stops cancel submitted jobs.
        """
        _ = graceful
        raw_job_ids = run.run_metadata.get(SLURM_JOB_IDS_METADATA_KEY)
        static_job_ids = (
            {str(name): str(job_id) for name, job_id in raw_job_ids.items()}
            if isinstance(raw_job_ids, dict)
            else {}
        )
        orchestration_job_id = run.run_metadata.get(
            SLURM_ORCHESTRATION_JOB_ID_METADATA_KEY
        )
        orchestration_job_ids = (
            {"orchestration": str(orchestration_job_id)}
            if orchestration_job_id
            else {}
        )
        if not (static_job_ids or orchestration_job_ids):
            logger.warning("No Slurm job metadata found for run `%s`.", run.id)
            return

        run_id = str(run.id)
        client = build_slurm_client(self.config)
        try:
            self._cancel_jobs(
                client=client,
                job_ids=static_job_ids,
                run_dir_for_key=lambda step_name: self._run_dir(
                    run_id, step_name
                ),
            )
            self._cancel_jobs(
                client=client,
                job_ids=orchestration_job_ids,
                run_dir_for_key=lambda _: self._orchestration_run_dir(run_id),
            )
        finally:
            client.runner.close()

    def _cancel_unfinished_jobs(
        self,
        client: SlurmClient,
        run_id: str,
        job_ids: Dict[str, str],
        statuses: Dict[str, Optional[ExecutionStatus]],
    ) -> None:
        """Cancel jobs that are not yet terminal.

        Args:
            client: Slurm client used to cancel jobs.
            run_id: Orchestrator run ID.
            job_ids: Mapping of step names to Slurm job IDs.
            statuses: Reconciled step statuses keyed by step name.
        """
        jobs_to_cancel: Dict[str, str] = {}
        for step_name, job_id in job_ids.items():
            status = statuses.get(step_name)
            if not (status and status.is_finished):
                jobs_to_cancel[step_name] = job_id
        self._cancel_jobs(
            client=client,
            job_ids=jobs_to_cancel,
            run_dir_for_key=lambda step_name: self._run_dir(run_id, step_name),
        )

    def _cancel_jobs(
        self,
        client: SlurmClient,
        job_ids: Dict[str, str],
        run_dir_for_key: Callable[[str], str],
    ) -> None:
        """Cancel Slurm jobs and persist cancellation sentinels.

        Args:
            client: Slurm client used to cancel jobs.
            job_ids: Mapping of stable job keys to Slurm job IDs.
            run_dir_for_key: Function returning the staging directory for a
                job key.
        """
        if not job_ids:
            return

        cancelled_steps = set(job_ids)
        try:
            client.cancel_jobs(list(job_ids.values()))
        except Exception:
            logger.warning(
                "Failed to cancel Slurm jobs in one request; retrying "
                "individually."
            )
            cancelled_steps = set()
            for step_name, job_id in job_ids.items():
                try:
                    client.cancel(job_id)
                except Exception:
                    logger.warning(
                        "Failed to cancel Slurm job `%s` for step `%s`.",
                        job_id,
                        step_name,
                    )
                else:
                    cancelled_steps.add(step_name)

        for job_key in cancelled_steps:
            try:
                run_dir = run_dir_for_key(job_key)
                client.runner.put_text(
                    f"{run_dir}/{CANCELLED_FILE}", "1\n", mode=0o600
                )
                self._cleanup_sensitive_files(client, run_dir)
            except Exception:
                logger.warning(
                    "Failed to write Slurm cancellation marker for job `%s`.",
                    job_key,
                )

    @staticmethod
    def _cleanup_sensitive_files(client: SlurmClient, run_dir: str) -> None:
        """Remove credential-bearing files for a submitted Slurm job.

        Args:
            client: Slurm client used to remove the files.
            run_dir: Per-job staging directory.
        """
        paths = [
            f"{run_dir}/{ENV_FILE}",
            f"{run_dir}/{REGISTRY_AUTH_FILE}",
            f"{run_dir}/{DOCKER_CONFIG_DIR}",
            f"{run_dir}/{ENROOT_CONFIG_DIR}",
        ]
        client.runner.run(
            "rm -rf -- " + " ".join(shlex.quote(path) for path in paths)
        )
