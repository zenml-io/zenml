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
"""Baseten step operator implementation."""

import tempfile
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)

from truss.base import truss_config
from truss.remote.remote_factory import RemoteFactory
from truss.remote.truss_remote import RemoteConfig
from truss_train import definitions, push

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.baseten.flavors import (
    BasetenStepOperatorConfig,
    BasetenStepOperatorSettings,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import Uri
from zenml.orchestrators.publish_utils import publish_step_run_metadata
from zenml.orchestrators.utils import shell_join
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.integrations.baseten.baseten_api import BasetenApiClient
    from zenml.models import PipelineSnapshotBase, StepRunResponse

logger = get_logger(__name__)

BASETEN_STEP_OPERATOR_DOCKER_IMAGE_KEY = "baseten_step_operator"
BASETEN_JOB_ID_METADATA_KEY = "baseten_job_id"
BASETEN_PROJECT_ID_METADATA_KEY = "baseten_training_project_id"
BASETEN_LOGS_URL_METADATA_KEY = "baseten_logs_url"

# truss `push()` authenticates via a named remote in ~/.trussrc; the operator
# writes it from the configured API key before pushing.
BASETEN_REMOTE_NAME = "baseten"
BASETEN_REMOTE_URL = "https://app.baseten.co"

# Baseten exposes both fully-qualified (TRAINING_JOB_*) and short job state
# names depending on the surface; map both defensively.
_BASETEN_STATE_TO_EXECUTION_STATUS = {
    "TRAINING_JOB_PENDING": ExecutionStatus.QUEUED,
    "TRAINING_JOB_CREATED": ExecutionStatus.INITIALIZING,
    "TRAINING_JOB_DEPLOYING": ExecutionStatus.PROVISIONING,
    "TRAINING_JOB_RUNNING": ExecutionStatus.RUNNING,
    "TRAINING_JOB_COMPLETED": ExecutionStatus.COMPLETED,
    "TRAINING_JOB_FAILED": ExecutionStatus.FAILED,
    "TRAINING_JOB_STOPPED": ExecutionStatus.STOPPED,
    "DEPLOY_FAILED": ExecutionStatus.FAILED,
    "CREATED": ExecutionStatus.INITIALIZING,
    "DEPLOYING": ExecutionStatus.PROVISIONING,
    "RUNNING": ExecutionStatus.RUNNING,
    "COMPLETED": ExecutionStatus.COMPLETED,
    "FAILED": ExecutionStatus.FAILED,
    "STOPPED": ExecutionStatus.STOPPED,
}


def _explain_submit_error(
    error: Exception,
    settings: BasetenStepOperatorSettings,
    is_command_step: bool,
) -> str:
    """Turn a Baseten job submission failure into an actionable message.

    Args:
        error: The exception raised by the truss ``push``.
        settings: The resolved step operator settings.
        is_command_step: Whether the step is a command step.

    Returns:
        A human-readable error message.
    """
    detail = str(error)
    # The actionable reason lives in the HTTP response body, not the generic
    # "400 Bad Request" message; read it defensively since the exception type
    # comes from a third-party (truss/requests) client.
    response = getattr(error, "response", None)
    body = (getattr(response, "text", "") or "").strip()
    combined = f"{detail} {body}".lower()

    hints = []
    if "base image" in combined:
        kind = "regular step" if not is_command_step else "step"
        hints.append(
            f"This {kind} submits a custom image, which requires the "
            "'custom base images' entitlement enabled for your Baseten "
            "organization (contact Baseten support). Regular @steps always "
            "need a custom image; to avoid it, run GPU work as a CommandStep "
            "on a public base image."
        )
    if settings.node_count > 1:
        hints.append(
            f"Multi-node jobs (node_count={settings.node_count}) require "
            "multi-node instance types enabled for your Baseten organization "
            "(contact Baseten support)."
        )

    message = f"Baseten rejected the training job submission: {detail}"
    if body:
        message += f" (Baseten response: {body[:500]})"
    if hints:
        message += " " + " ".join(hints)
    return message


class BasetenStepOperator(BaseStepOperator):
    """Step operator that runs a step as a Baseten training job."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the step operator.

        Args:
            *args: Positional arguments forwarded to the base class.
            **kwargs: Keyword arguments forwarded to the base class.
        """
        super().__init__(*args, **kwargs)
        self._api: Optional["BasetenApiClient"] = None

    @property
    def api(self) -> "BasetenApiClient":
        """Lazily constructed Baseten REST API client.

        Returns:
            The Baseten REST API client.
        """
        if self._api is None:
            from zenml.integrations.baseten.baseten_api import (
                BasetenApiClient,
            )

            self._api = BasetenApiClient(
                self.config.api_key.get_secret_value()
            )
        return self._api

    @property
    def config(self) -> BasetenStepOperatorConfig:
        """Get the Baseten step operator configuration.

        Returns:
            The Baseten step operator configuration.
        """
        return cast(BasetenStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Get the settings class for the Baseten step operator.

        Returns:
            The Baseten step operator settings class.
        """
        return BasetenStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Get the stack validator for the Baseten step operator.

        Returns:
            The stack validator.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Baseten step operator runs code remotely and needs "
                    "to write files into the artifact store, but the artifact "
                    f"store `{stack.artifact_store.name}` of the active stack "
                    "is local. Please ensure that your stack contains a "
                    "remote artifact store when using the Baseten step "
                    "operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Baseten step operator runs code remotely and needs "
                    "to push/pull Docker images, but the container registry "
                    f"`{container_registry.name}` of the active stack is "
                    "local. Please ensure that your stack contains a remote "
                    "container registry when using the Baseten step operator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def get_docker_builds(
        self, snapshot: "PipelineSnapshotBase"
    ) -> List["BuildConfiguration"]:
        """Get the Docker build configurations for the Baseten step operator.

        Args:
            snapshot: The pipeline snapshot.

        Returns:
            A list of Docker build configurations.
        """
        builds = []
        for step_name, step in snapshot.step_configurations.items():
            if step.config.uses_step_operator(self.name):
                builds.append(
                    BuildConfiguration(
                        key=BASETEN_STEP_OPERATOR_DOCKER_IMAGE_KEY,
                        settings=step.config.docker_settings,
                        step_name=step_name,
                    )
                )

        return builds

    def _build_environment(
        self,
        environment: Dict[str, str],
        secrets: Dict[str, str],
    ) -> Dict[str, Any]:
        """Build the Baseten runtime environment from the step environment.

        Variables named in the ``secrets`` mapping are replaced with Baseten
        secret references so their values are never inlined into the job
        config; everything else is passed through as-is.

        Args:
            environment: The environment variables for the step.
            secrets: Mapping of environment variable name to an existing
                Baseten secret name.

        Returns:
            The runtime environment with plain strings and secret references.
        """
        runtime_environment: Dict[str, Any] = {}
        for key, value in environment.items():
            if key in secrets:
                runtime_environment[key] = definitions.SecretReference(
                    name=secrets[key]
                )
            else:
                runtime_environment[key] = value
        return runtime_environment

    def _configure_truss_remote(self) -> None:
        """Write the Baseten remote into truss config so push() can auth.

        ``push()`` authenticates through a named remote in ~/.trussrc; this
        writes/updates it from the configured API key.
        """
        RemoteFactory.update_remote_config(
            RemoteConfig(
                name=BASETEN_REMOTE_NAME,
                configs={
                    "remote_provider": "baseten",
                    "remote_url": BASETEN_REMOTE_URL,
                    "api_key": self.config.api_key.get_secret_value(),
                },
            )
        )

    def _docker_auth(self) -> Optional[Any]:
        """Build Baseten Docker auth from the configured registry secret.

        Baseten only accepts registry credentials as a reference to a
        pre-existing Baseten secret, never inline.

        Returns:
            A Baseten ``DockerAuth`` object, or None for public images when no
            registry secret is configured.
        """
        if not self.config.registry_auth_secret:
            return None

        container_registry = Client().active_stack.container_registry
        assert container_registry is not None
        return definitions.DockerAuth(
            auth_method=truss_config.DockerAuthType.REGISTRY_SECRET,
            registry=container_registry.config.uri,
            registry_secret_docker_auth=definitions.RegistrySecretDockerAuth(
                secret_ref=definitions.SecretReference(
                    name=self.config.registry_auth_secret
                ),
            ),
        )

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Submit a step run as a Baseten training job.

        Args:
            info: The step run information.
            entrypoint_command: The entrypoint command for the step.
            environment: The environment variables for the step.

        Raises:
            RuntimeError: If multi-node execution is requested for a regular
                step.
        """
        settings = cast(BasetenStepOperatorSettings, self.get_settings(info))
        is_command_step = info.config.command is not None

        # A multi-node job runs the same entrypoint on every node. A regular
        # step would therefore duplicate its artifacts, outputs and logs across
        # nodes, so only command steps (which own their distributed launch) may
        # scale out. This runs at submit time because dynamic pipelines execute
        # from a server-side snapshot where no compile-time hook is available.
        if settings.node_count > 1 and not is_command_step:
            raise RuntimeError(
                f"The step `{info.pipeline_step_name}` requests "
                f"node_count={settings.node_count} but is a regular step. "
                "Running a regular step on multiple nodes would duplicate its "
                "artifacts, outputs and logs across every node. Use a "
                "CommandStep that owns its distributed launch instead. Wrap "
                "the launcher in a shell so Baseten's per-node variables "
                "(BT_GROUP_SIZE, BT_NODE_RANK, BT_LEADER_ADDR, BT_NUM_GPUS) "
                "expand on each node, e.g. "
                '`CommandStep(command=["bash", "-lc", "torchrun '
                "--nnodes=$BT_GROUP_SIZE --node-rank=$BT_NODE_RANK "
                "--master-addr=$BT_LEADER_ADDR --master-port=29500 "
                '--nproc-per-node=$BT_NUM_GPUS train.py"], '
                f'step_operator="{self.name}")`. Keep node_count=1 for '
                "regular steps; see the Baseten step-operator docs "
                "(multi-node distributed training) for the full pattern."
            )

        image_name = info.get_image(key=BASETEN_STEP_OPERATOR_DOCKER_IMAGE_KEY)

        # Compute resources come from ResourceSettings (the standard ZenML
        # place for them); only pass cpu_count/memory when set, since truss
        # `Compute` types them as int/str and applies its own defaults when
        # omitted. gpu_count defaults to 1 only when unset (0 stays 0).
        resources = info.config.resource_settings
        gpu_count = (
            resources.gpu_count if resources.gpu_count is not None else 1
        )
        compute_kwargs: Dict[str, Any] = {
            "node_count": settings.node_count,
            "accelerator": truss_config.AcceleratorSpec(
                accelerator=settings.accelerator,
                count=gpu_count,
            ),
        }
        if resources.cpu_count is not None:
            compute_kwargs["cpu_count"] = int(resources.cpu_count)
        if resources.memory is not None:
            compute_kwargs["memory"] = resources.memory

        # Cache / checkpointing are opt-in (default disabled); only attach the
        # config objects when enabled so the job keeps Baseten's defaults.
        runtime_kwargs: Dict[str, Any] = {
            "start_commands": [shell_join(entrypoint_command)],
            "environment_variables": self._build_environment(
                environment=environment,
                secrets=settings.secrets,
            ),
        }
        if settings.enable_cache:
            runtime_kwargs["cache_config"] = definitions.CacheConfig(
                enabled=True,
                enable_legacy_hf_mount=settings.cache_enable_legacy_hf_mount,
                require_cache_affinity=settings.cache_require_affinity,
            )
        if settings.enable_checkpointing:
            runtime_kwargs["checkpointing_config"] = (
                definitions.CheckpointingConfig(enabled=True)
            )

        project = definitions.TrainingProject(
            name=self.config.project,
            job=definitions.TrainingJob(
                image=definitions.Image(
                    base_image=image_name, docker_auth=self._docker_auth()
                ),
                compute=definitions.Compute(**compute_kwargs),
                runtime=definitions.Runtime(**runtime_kwargs),
                # The ZenML image is the entire environment; do not extract an
                # uploaded working directory on top of it.
                enable_baseten_workdir=False,
            ),
        )

        # Push from an empty temp dir so the local working directory is not
        # uploaded: the Docker image is the single source of truth for code.
        self._configure_truss_remote()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = push(
                    config=project,
                    source_dir=Path(tmpdir),
                    remote=BASETEN_REMOTE_NAME,
                )
        except Exception as e:
            raise RuntimeError(
                _explain_submit_error(e, settings, is_command_step)
            ) from e

        job_id = result["id"]
        project_id = result["training_project_id"]
        metadata: Dict[str, Any] = {
            BASETEN_JOB_ID_METADATA_KEY: job_id,
            BASETEN_PROJECT_ID_METADATA_KEY: project_id,
            BASETEN_LOGS_URL_METADATA_KEY: Uri(
                f"{BASETEN_REMOTE_URL}/training/project/{project_id}"
                f"/logs/{job_id}"
            ),
        }

        # The job ids let status checks and cancellation find the job. If
        # persisting them fails, the job is already running on Baseten, so let
        # it continue rather than failing the step over bookkeeping; log loudly
        # (with the ids) so an otherwise untracked, billable job can be found.
        try:
            publish_step_run_metadata(info.step_run_id, {self.id: metadata})
            info.step_run.run_metadata.update(metadata)
        except Exception:
            logger.error(
                "Failed to persist Baseten job ids for step `%s`. The job is "
                "running on Baseten (job_id=%s, project_id=%s) but status "
                "checks and cancellation will not work without these ids. Stop "
                "it from the Baseten dashboard if needed.",
                info.pipeline_step_name,
                job_id,
                project_id,
            )

    def _extract_job_and_project_id(
        self, step_run: "StepRunResponse"
    ) -> Optional[Tuple[str, str]]:
        """Recover the (project_id, job_id) for a step run from its metadata.

        Args:
            step_run: The step run.

        Returns:
            The (project_id, job_id) tuple, or None if not recorded.
        """
        job_id = step_run.run_metadata.get(BASETEN_JOB_ID_METADATA_KEY)
        project_id = step_run.run_metadata.get(BASETEN_PROJECT_ID_METADATA_KEY)
        if job_id is None or project_id is None:
            return None
        return str(project_id), str(job_id)

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Get the status of a submitted Baseten training job.

        Args:
            step_run: The step run.

        Returns:
            The execution status. Returns FAILED if the job ids are missing or
            the job no longer exists.
        """
        ids = self._extract_job_and_project_id(step_run)
        if ids is None:
            return ExecutionStatus.FAILED

        project_id, job_id = ids
        state = self.api.get_job_status(project_id, job_id)
        if state is None:
            return ExecutionStatus.FAILED

        return _BASETEN_STATE_TO_EXECUTION_STATUS.get(
            state, ExecutionStatus.RUNNING
        )

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancel a submitted Baseten training job.

        Args:
            step_run: The step run.
        """
        ids = self._extract_job_and_project_id(step_run)
        if ids is None:
            return
        project_id, job_id = ids
        self.api.stop_job(project_id, job_id)
