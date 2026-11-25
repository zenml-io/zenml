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
"""HuggingFace Jobs step operator implementation."""

import os
from enum import Enum
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

from zenml.config.build_configuration import BuildConfiguration
from zenml.constants import (
    METADATA_ORCHESTRATOR_LOGS_URL,
    METADATA_ORCHESTRATOR_RUN_ID,
    METADATA_ORCHESTRATOR_URL,
)
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.exceptions import RunInterruptedException, RunStoppedException
from zenml.integrations.huggingface.flavors.huggingface_jobs_step_operator_flavor import (
    HuggingFaceJobsStepOperatorConfig,
    HuggingFaceJobsStepOperatorSettings,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType, Uri
from zenml.orchestrators.publish_utils import publish_step_run_metadata
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase, StepRunResponse

logger = get_logger(__name__)

HUGGINGFACE_JOBS_DOCKER_IMAGE_KEY = "huggingface_jobs_step_operator"
STEP_JOB_ID_METADATA_KEY = "hf_job_id"
_HF_JOB_NAMESPACE_METADATA_KEY = "hf_job_namespace"

_HF_JOBS_MIN_VERSION = "0.34.0"

_HF_TOKEN_ENV_KEYS = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN")


def _check_hf_jobs_availability() -> None:
    """Verify that the installed huggingface_hub supports the Jobs API.

    Raises:
        RuntimeError: If huggingface_hub is missing or too old to expose the
            Jobs API symbols.
    """
    try:
        from huggingface_hub import (  # noqa: F401
            JobStage,
            cancel_job,
            get_token,
            inspect_job,
            run_job,
        )
    except ImportError as exc:
        raise RuntimeError(
            "The HuggingFace Jobs step operator requires "
            f"`huggingface_hub>={_HF_JOBS_MIN_VERSION},<2.0.0` with the Jobs "
            "API available. Install or upgrade with: "
            f"`pip install 'huggingface_hub>={_HF_JOBS_MIN_VERSION},<2.0.0'`"
        ) from exc


def _resolve_token(config: HuggingFaceJobsStepOperatorConfig) -> str:
    """Resolve the HF token used for Jobs API calls.

    Resolution order:
    1. Explicit ``config.token`` on the step operator component.
    2. ``huggingface_hub.get_token()`` (checks OIDC, ``HF_TOKEN``, and cached
       login across huggingface_hub 0.x and 1.x).
    3. Legacy ``HUGGING_FACE_HUB_TOKEN`` environment variable.

    Args:
        config: The step operator config.

    Returns:
        A Hugging Face API token string.

    Raises:
        RuntimeError: If no token can be resolved.
    """
    if config.token:
        return config.token

    from huggingface_hub import get_token

    token = get_token()
    if token:
        return str(token)

    legacy_token = os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if legacy_token:
        return legacy_token

    raise RuntimeError(
        "No Hugging Face token found. Please either: "
        "(1) set the `token` field on the step operator component, "
        "(2) set the `HF_TOKEN` environment variable, or "
        "(3) run `hf auth login` (or `huggingface-cli login`)."
    )


def split_environment(
    environment: Dict[str, str],
    pass_as_secrets: bool,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Split environment variables into plain env and HF encrypted secrets.

    Any step-supplied Hugging Face token keys are always routed into
    ``secrets`` (never ``plain_env``) so they are not exposed in job specs.

    Args:
        environment: The full environment dict from ZenML.
        pass_as_secrets: Whether to route all vars through HF secrets.

    Returns:
        A tuple of ``(plain_env, secrets)``.
    """
    if pass_as_secrets:
        return {}, dict(environment)

    plain_env = dict(environment)
    secrets: Dict[str, str] = {}

    for key in _HF_TOKEN_ENV_KEYS:
        if key in plain_env:
            secrets[key] = plain_env.pop(key)

    return plain_env, secrets


class HuggingFaceJobsStepOperator(BaseStepOperator):
    """Step operator that runs individual steps as Hugging Face Jobs.

    HF Jobs execute Docker containers on Hugging Face infrastructure,
    supporting both CPU and GPU hardware flavors. This operator submits
    the ZenML step entrypoint command as a Job and tracks its execution
    through the async step operator lifecycle.

    Requirements:
        - A Hugging Face Pro, Team, or Enterprise account with Jobs access.
        - A remote artifact store (the Job cannot access local files).
        - A remote container registry and image builder (the Job pulls
          the built Docker image).
    """

    @property
    def config(self) -> HuggingFaceJobsStepOperatorConfig:
        """Returns the step operator configuration.

        Returns:
            The configuration.
        """
        return cast(HuggingFaceJobsStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for per-step overrides.

        Returns:
            The settings class.
        """
        return HuggingFaceJobsStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack for remote execution requirements.

        Returns:
            A validator that checks for remote artifact store and
            container registry.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The HuggingFace Jobs step operator runs steps on "
                    "remote HF infrastructure and needs to read/write "
                    "artifacts, but the artifact store "
                    f"`{stack.artifact_store.name}` of the active stack "
                    "is local. Please use a remote artifact store "
                    "(e.g., S3, GCS, Azure)."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The HuggingFace Jobs step operator runs steps on "
                    "remote HF infrastructure and needs to pull Docker "
                    "images, but the container registry "
                    f"`{container_registry.name}` of the active stack "
                    "is local. Please use a remote container registry."
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
        """Gets the Docker build configurations for steps using this operator.

        Args:
            snapshot: The pipeline snapshot.

        Returns:
            A list of Docker build configurations.
        """
        builds = []
        for step_name, step in snapshot.step_configurations.items():
            if step.config.uses_step_operator(self.name):
                build = BuildConfiguration(
                    key=HUGGINGFACE_JOBS_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Submit a step as a HuggingFace Job (non-blocking).

        Creates the remote HF Job and returns immediately. The job
        identity is persisted in step run metadata so that
        ``get_status`` and ``cancel`` can recover it later. If metadata
        publication fails, the remote job is canceled before re-raising.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables for the step.

        Raises:
            Exception: If job submission or metadata publication fails.
        """
        _check_hf_jobs_availability()

        from huggingface_hub import cancel_job, constants, run_job

        if not info.config.resource_settings.empty:
            logger.warning(
                "Specifying custom step resources via `ResourceSettings` is "
                "not supported for the HuggingFace Jobs step operator. "
                "Configure compute resources using `hardware_flavor` in "
                "`HuggingFaceJobsStepOperatorSettings` or via "
                "`zenml step-operator update %s --hardware_flavor=<FLAVOR>`.",
                self.name,
            )

        settings = cast(
            HuggingFaceJobsStepOperatorSettings, self.get_settings(info)
        )

        image = info.get_image(key=HUGGINGFACE_JOBS_DOCKER_IMAGE_KEY)
        token = _resolve_token(self.config)

        plain_env, secrets = split_environment(
            environment, self.config.pass_env_as_secrets
        )

        if secrets and getattr(constants, "HF_DEBUG", False):
            logger.warning(
                "`HF_DEBUG` is enabled in `huggingface_hub`. Debug HTTP logs "
                "may include request bodies containing ZenML step secrets."
            )

        logger.info(
            "Submitting HuggingFace Job for step '%s' (run '%s') with image "
            "'%s' and hardware flavor '%s'.",
            info.pipeline_step_name,
            info.run_name,
            image,
            settings.hardware_flavor or "cpu-basic",
        )

        info.force_write_logs()

        job = run_job(
            image=image,
            command=entrypoint_command,
            env=plain_env or None,
            secrets=secrets or None,
            # hub 0.36.x typed `flavor` as SpaceHardware even though the API
            # accepts any Jobs flavor string (hub 1.x widened it to str).
            flavor=cast(Any, settings.hardware_flavor),
            timeout=settings.timeout,
            namespace=settings.namespace,
            token=token,
        )
        logger.info(
            "HuggingFace Job created: id=%s, url=%s",
            job.id,
            job.url,
        )

        owner = getattr(job, "owner", None)
        owner_name = getattr(owner, "name", None) if owner else None
        resolved_namespace = settings.namespace or (
            str(owner_name) if owner_name else None
        )

        step_metadata: Dict[str, MetadataType] = {
            STEP_JOB_ID_METADATA_KEY: str(job.id),
            METADATA_ORCHESTRATOR_RUN_ID: str(job.id),
            METADATA_ORCHESTRATOR_URL: Uri(str(job.url)),
            METADATA_ORCHESTRATOR_LOGS_URL: Uri(str(job.url)),
        }
        if resolved_namespace:
            step_metadata[_HF_JOB_NAMESPACE_METADATA_KEY] = resolved_namespace

        # Persist job identity in server metadata (for dashboard links and
        # cross-process recovery) and in the in-memory step run (so wait()
        # can poll immediately without re-hydration). If publishing fails,
        # cancel the remote job so it does not keep running unmonitored.
        try:
            publish_step_run_metadata(
                step_run_id=info.step_run_id,
                step_run_metadata={self.id: step_metadata},
            )
            info.step_run.run_metadata[STEP_JOB_ID_METADATA_KEY] = str(job.id)
            if resolved_namespace:
                info.step_run.run_metadata[_HF_JOB_NAMESPACE_METADATA_KEY] = (
                    resolved_namespace
                )
        except Exception:
            try:
                cancel_job(
                    job_id=str(job.id),
                    namespace=resolved_namespace,
                    token=token,
                )
            except Exception:
                logger.exception(
                    "Failed to cancel HuggingFace Job '%s' (%s) after "
                    "metadata publication failed.",
                    job.id,
                    job.url,
                )
            raise

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Get the execution status of a submitted HuggingFace Job.

        Args:
            step_run: The step run to check.

        Returns:
            The current execution status.
        """
        _check_hf_jobs_availability()

        from huggingface_hub import JobStage, inspect_job

        token = _resolve_token(self.config)
        job_id, namespace = self._get_job_identity(step_run)

        job_info = inspect_job(job_id=job_id, namespace=namespace, token=token)
        stage = job_info.status.stage

        if stage == JobStage.COMPLETED:
            return ExecutionStatus.COMPLETED
        if stage in (JobStage.ERROR, JobStage.CANCELED, JobStage.DELETED):
            stage_label = (
                stage.value if isinstance(stage, Enum) else str(stage)
            )
            message = job_info.status.message or "No error message provided."
            logger.error(
                "HuggingFace Job %s ended with stage=%s. Message: %s",
                job_id,
                stage_label,
                message,
            )
            return ExecutionStatus.FAILED
        return ExecutionStatus.RUNNING

    def wait(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Wait for a HuggingFace Job to finish, canceling on stop/interrupt.

        Delegates polling and server-status fallback to
        ``BaseStepOperator.wait()`` and cancels the remote HF Job if the wait
        is interrupted or stopped.

        Args:
            step_run: The step run to wait for.

        Returns:
            The final execution status.

        Raises:
            KeyboardInterrupt: If interrupted by the user while waiting.
            RunInterruptedException: If step execution is interrupted by a
                signal while waiting.
            RunStoppedException: If the pipeline or step run is stopped while
                waiting.
        """
        try:
            status = super().wait(step_run)
        except (
            KeyboardInterrupt,
            RunStoppedException,
            RunInterruptedException,
        ):
            self.cancel(step_run)
            raise

        if status in (ExecutionStatus.STOPPED, ExecutionStatus.STOPPING):
            self.cancel(step_run)

        return status

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancel a submitted HuggingFace Job (best-effort).

        Args:
            step_run: The step run to cancel.
        """
        _check_hf_jobs_availability()

        token = _resolve_token(self.config)
        job_id, namespace = self._get_job_identity(step_run)
        self._best_effort_cancel(job_id, namespace, token)

    def _get_job_identity(
        self, step_run: "StepRunResponse"
    ) -> Tuple[str, Optional[str]]:
        """Recover HF Job identity from step run metadata.

        Args:
            step_run: The step run containing persisted metadata.

        Returns:
            A tuple of ``(job_id, namespace)``.

        Raises:
            RuntimeError: If the job ID metadata key is missing.
        """
        metadata = step_run.run_metadata
        job_id = metadata.get(STEP_JOB_ID_METADATA_KEY) or metadata.get(
            METADATA_ORCHESTRATOR_RUN_ID
        )
        if not job_id:
            raise RuntimeError(
                f"Cannot find HuggingFace Job ID in step run metadata. "
                f"Expected key '{STEP_JOB_ID_METADATA_KEY}' or "
                f"'{METADATA_ORCHESTRATOR_RUN_ID}'. Available keys: "
                f"{list(metadata.keys())}"
            )
        namespace = metadata.get(_HF_JOB_NAMESPACE_METADATA_KEY)
        return str(job_id), str(namespace) if namespace else None

    @staticmethod
    def _best_effort_cancel(
        job_id: str,
        namespace: Optional[str],
        token: str,
    ) -> None:
        """Attempt to cancel a remote HF Job, suppressing errors.

        Args:
            job_id: The HF Job ID.
            namespace: The HF namespace.
            token: The HF API token.
        """
        from huggingface_hub import cancel_job

        try:
            cancel_job(job_id=job_id, namespace=namespace, token=token)
            logger.info("HuggingFace Job %s cancel request sent.", job_id)
        except Exception:
            logger.debug(
                "Failed to cancel HuggingFace Job %s.",
                job_id,
                exc_info=True,
            )
