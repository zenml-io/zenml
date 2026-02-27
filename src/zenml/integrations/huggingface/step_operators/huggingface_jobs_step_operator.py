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

import random
import time
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
STEP_JOB_NAME_METADATA_KEY = "job_name"
_HF_JOB_NAMESPACE_METADATA_KEY = "hf_job_namespace"

_HF_JOBS_MIN_VERSION = "0.30.0"

_HF_TOKEN_ENV_KEYS = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN")

_HF_JOBS_POLL_MAX_CONSECUTIVE_ERRORS = 3
_HF_JOBS_POLL_BACKOFF_CAP_SECONDS = 300.0


def _check_hf_jobs_availability() -> None:
    """Verify that the installed huggingface_hub supports the Jobs API.

    Checks both that the package is installed and that the version is
    new enough to include the Jobs API (>= 0.30.0).

    Raises:
        RuntimeError: If huggingface_hub is missing, too old, or lacks
            the Jobs API symbols.
    """
    installed_version: Optional[str] = None
    try:
        from importlib.metadata import version

        installed_version = version("huggingface_hub")
    except Exception:
        pass

    if installed_version is None:
        raise RuntimeError(
            f"`huggingface_hub` is not installed. The HuggingFace Jobs "
            f"step operator requires `huggingface_hub>="
            f"{_HF_JOBS_MIN_VERSION}`. Install it with: "
            f"`pip install 'huggingface_hub>={_HF_JOBS_MIN_VERSION}'`"
        )

    # Best-effort version comparison using packaging if available,
    # falling back to a simple tuple comparison.
    try:
        from packaging.version import Version

        if Version(installed_version) < Version(_HF_JOBS_MIN_VERSION):
            raise RuntimeError(
                f"The HuggingFace Jobs step operator requires "
                f"`huggingface_hub>={_HF_JOBS_MIN_VERSION}`, but "
                f"version `{installed_version}` is installed. "
                f"Upgrade with: `pip install 'huggingface_hub>="
                f"{_HF_JOBS_MIN_VERSION}'`"
            )
    except ImportError:
        # packaging not available — compare version tuples
        try:
            installed_tuple = tuple(
                int(x) for x in installed_version.split(".")[:3]
            )
            min_tuple = tuple(
                int(x) for x in _HF_JOBS_MIN_VERSION.split(".")[:3]
            )
            if installed_tuple < min_tuple:
                raise RuntimeError(
                    f"The HuggingFace Jobs step operator requires "
                    f"`huggingface_hub>={_HF_JOBS_MIN_VERSION}`, but "
                    f"version `{installed_version}` is installed. "
                    f"Upgrade with: `pip install 'huggingface_hub>="
                    f"{_HF_JOBS_MIN_VERSION}'`"
                )
        except (ValueError, TypeError):
            pass  # unparseable version — fall through to capability check

    # Final capability check: the Jobs API symbols must be importable.
    try:
        from huggingface_hub import run_job  # noqa: F401
    except ImportError:
        raise RuntimeError(
            f"The installed `huggingface_hub` ({installed_version}) does "
            f"not expose the Jobs API. Please upgrade: "
            f"`pip install 'huggingface_hub>={_HF_JOBS_MIN_VERSION}'`"
        )


def _resolve_token(config: HuggingFaceJobsStepOperatorConfig) -> str:
    """Resolve the HF token from config or environment.

    Falls back to huggingface_hub's cached token if no explicit token
    is configured.

    Args:
        config: The step operator config.

    Returns:
        A Hugging Face API token string.

    Raises:
        RuntimeError: If no token can be resolved.
    """
    if config.token:
        return config.token

    import os

    env_token = os.environ.get("HF_TOKEN") or os.environ.get(
        "HUGGING_FACE_HUB_TOKEN"
    )
    if env_token:
        return env_token

    try:
        from huggingface_hub import HfFolder

        cached = HfFolder.get_token()
        if cached:
            return str(cached)
    except Exception:
        pass

    raise RuntimeError(
        "No Hugging Face token found. Please either: "
        "(1) set the `token` field on the step operator component, "
        "(2) set the HF_TOKEN environment variable, or "
        "(3) run `huggingface-cli login`."
    )


def _resolve_space_hardware(
    hardware_flavor_str: Optional[str],
) -> Optional[Any]:
    """Convert a hardware flavor string to a SpaceHardware enum value.

    Tries the public import path first, then falls back to the private
    module. Validates the flavor string and provides actionable errors.

    Args:
        hardware_flavor_str: The hardware flavor string (e.g. 'a10g-small').

    Returns:
        A SpaceHardware enum value, or None if no flavor was specified.

    Raises:
        RuntimeError: If SpaceHardware cannot be imported or the flavor
            string is invalid.
    """
    if not hardware_flavor_str:
        return None

    space_hw_cls: Any = None
    try:
        import huggingface_hub

        space_hw_cls = getattr(huggingface_hub, "SpaceHardware", None)
    except ImportError:
        pass

    if space_hw_cls is None:
        try:
            from huggingface_hub._space_api import (
                SpaceHardware as _SpaceHardware,
            )

            space_hw_cls = _SpaceHardware
        except ImportError:
            raise RuntimeError(
                f"Cannot import SpaceHardware from huggingface_hub. "
                f"Upgrade with: `pip install 'huggingface_hub>="
                f"{_HF_JOBS_MIN_VERSION}'`"
            )

    # Try enum-by-value first, then attribute lookup with normalization
    try:
        return space_hw_cls(hardware_flavor_str)
    except ValueError:
        pass

    normalized = hardware_flavor_str.upper().replace("-", "_")
    hw = getattr(space_hw_cls, normalized, None)
    if hw is not None:
        return hw

    raise RuntimeError(
        f"Invalid hardware flavor '{hardware_flavor_str}'. "
        f"Run `hf jobs hardware` to see available options."
    )


def split_environment(
    environment: Dict[str, str],
    pass_as_secrets: bool,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Split environment variables into plain env and HF encrypted secrets.

    HF token keys are always stripped from both dicts to prevent
    accidental leakage. The step operator injects the resolved token
    separately as an encrypted secret.

    Args:
        environment: The full environment dict from ZenML.
        pass_as_secrets: Whether to route vars through HF secrets.

    Returns:
        A tuple of (plain_env, secrets), with token keys removed.
    """
    if pass_as_secrets:
        plain_env: Dict[str, str] = {}
        secrets = dict(environment)
    else:
        plain_env = dict(environment)
        secrets = {}

    # Always strip token keys — the operator injects the canonical
    # token into secrets separately.
    for key in _HF_TOKEN_ENV_KEYS:
        plain_env.pop(key, None)
        secrets.pop(key, None)

    return plain_env, secrets


class HuggingFaceJobsStepOperator(BaseStepOperator):
    """Step operator that runs individual steps as Hugging Face Jobs.

    HF Jobs execute Docker containers on Hugging Face infrastructure,
    supporting both CPU and GPU hardware flavors. This operator submits
    the ZenML step entrypoint command as a Job, polls until completion,
    and optionally streams logs back to ZenML.

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
        ``get_status`` and ``cancel`` can recover it later.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables for the step.
        """
        _check_hf_jobs_availability()

        from huggingface_hub import run_job

        settings = cast(
            HuggingFaceJobsStepOperatorSettings, self.get_settings(info)
        )

        image = info.get_image(key=HUGGINGFACE_JOBS_DOCKER_IMAGE_KEY)
        token = _resolve_token(self.config)

        hardware_flavor_str = (
            settings.hardware_flavor or self.config.hardware_flavor
        )
        hardware_flavor = _resolve_space_hardware(hardware_flavor_str)
        timeout = settings.timeout or self.config.timeout
        namespace = settings.namespace or self.config.namespace

        plain_env, secrets = split_environment(
            environment, self.config.pass_env_as_secrets
        )

        # Inject the resolved HF token as encrypted secrets so user
        # code can interact with the Hub (push/pull models, datasets).
        for key in _HF_TOKEN_ENV_KEYS:
            secrets[key] = token

        job_name = f"zenml-{info.run_name}-{info.pipeline_step_name}"[:63]
        logger.info(
            "Submitting HuggingFace Job '%s' with image '%s' "
            "and hardware flavor '%s'.",
            job_name,
            image,
            hardware_flavor_str or "cpu-basic",
        )

        info.force_write_logs()

        job = run_job(
            image=image,
            command=entrypoint_command,
            env=plain_env or None,
            secrets=secrets or None,
            flavor=hardware_flavor,
            timeout=timeout,
            namespace=namespace,
            token=token,
        )
        logger.info(
            "HuggingFace Job created: id=%s, url=%s",
            job.id,
            job.url,
        )

        # Persist job identity in server metadata (for dashboard links
        # and cross-process recovery) and in the in-memory step run
        # (so wait() can poll immediately without re-hydration).
        try:
            step_metadata: Dict[str, MetadataType] = {
                STEP_JOB_NAME_METADATA_KEY: str(job.id),
                METADATA_ORCHESTRATOR_RUN_ID: str(job.id),
                METADATA_ORCHESTRATOR_URL: Uri(str(job.url)),
                METADATA_ORCHESTRATOR_LOGS_URL: Uri(str(job.url)),
            }
            if namespace:
                step_metadata[_HF_JOB_NAMESPACE_METADATA_KEY] = namespace
            publish_step_run_metadata(
                step_run_id=info.step_run_id,
                step_run_metadata={self.id: step_metadata},
            )
        except Exception:
            logger.debug(
                "Failed to publish HuggingFace Job metadata.",
                exc_info=True,
            )

        info.step_run.run_metadata[STEP_JOB_NAME_METADATA_KEY] = str(job.id)
        if namespace:
            info.step_run.run_metadata[_HF_JOB_NAMESPACE_METADATA_KEY] = (
                namespace
            )

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Get the execution status of a submitted HuggingFace Job.

        Args:
            step_run: The step run to check.

        Returns:
            The current execution status.

        Raises:
            RuntimeError: If the job identity metadata is missing.
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
            return ExecutionStatus.FAILED
        return ExecutionStatus.RUNNING

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancel a submitted HuggingFace Job (best-effort).

        Args:
            step_run: The step run to cancel.
        """
        _check_hf_jobs_availability()

        from huggingface_hub import cancel_job

        token = _resolve_token(self.config)
        job_id, namespace = self._get_job_identity(step_run)
        self._best_effort_cancel(cancel_job, job_id, namespace, token)

    def wait(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Wait for a HuggingFace Job to finish.

        Overrides the base class to use HF-specific polling behavior:
        configurable poll interval, transient error retry with backoff,
        and optional log streaming.

        Args:
            step_run: The step run to wait for.

        Returns:
            The final execution status.
        """
        _check_hf_jobs_availability()

        from huggingface_hub import (
            JobStage,
            cancel_job,
            fetch_job_logs,
            inspect_job,
        )

        token = _resolve_token(self.config)
        job_id, namespace = self._get_job_identity(step_run)

        consecutive_errors = 0
        log_offset = 0

        try:
            while True:
                try:
                    job_info = inspect_job(
                        job_id=job_id,
                        namespace=namespace,
                        token=token,
                    )
                    consecutive_errors = 0
                except Exception as poll_err:
                    consecutive_errors += 1
                    if (
                        consecutive_errors
                        >= _HF_JOBS_POLL_MAX_CONSECUTIVE_ERRORS
                    ):
                        logger.error(
                            "Failed to poll HuggingFace Job %s "
                            "after %d consecutive errors. "
                            "Last error: %s",
                            job_id,
                            consecutive_errors,
                            poll_err,
                        )
                        return ExecutionStatus.FAILED

                    backoff = min(
                        self.config.poll_interval_seconds
                        * (2**consecutive_errors),
                        _HF_JOBS_POLL_BACKOFF_CAP_SECONDS,
                    )
                    jitter = random.uniform(0, backoff * 0.1)
                    logger.warning(
                        "Transient error polling HF Job %s "
                        "(attempt %d/%d): %s. Retrying in %.1fs.",
                        job_id,
                        consecutive_errors,
                        _HF_JOBS_POLL_MAX_CONSECUTIVE_ERRORS,
                        poll_err,
                        backoff + jitter,
                    )
                    time.sleep(backoff + jitter)
                    continue

                stage = job_info.status.stage

                if self.config.stream_logs:
                    try:
                        logs = list(
                            fetch_job_logs(
                                job_id=job_id,
                                namespace=namespace,
                                token=token,
                            )
                        )
                        for line in logs[log_offset:]:
                            logger.info("[HF Job] %s", line.rstrip())
                        log_offset = len(logs)
                    except Exception:
                        logger.debug(
                            "Failed to fetch job logs (job may still "
                            "be initializing).",
                            exc_info=True,
                        )

                if stage == JobStage.COMPLETED:
                    logger.info(
                        "HuggingFace Job %s completed successfully.",
                        job_id,
                    )
                    return ExecutionStatus.COMPLETED

                if stage in (
                    JobStage.ERROR,
                    JobStage.CANCELED,
                    JobStage.DELETED,
                ):
                    message = (
                        job_info.status.message or "No error message provided."
                    )
                    stage_str = (
                        stage.value if hasattr(stage, "value") else stage
                    )
                    logger.error(
                        "HuggingFace Job %s ended with stage=%s. Message: %s",
                        job_id,
                        stage_str,
                        message,
                    )
                    return ExecutionStatus.FAILED

                logger.debug(
                    "HuggingFace Job %s stage: %s. Polling again in %ss.",
                    job_id,
                    stage.value if hasattr(stage, "value") else stage,
                    self.config.poll_interval_seconds,
                )
                time.sleep(self.config.poll_interval_seconds)

        except KeyboardInterrupt:
            logger.warning(
                "Interrupt received. Canceling HuggingFace Job %s...",
                job_id,
            )
            self._best_effort_cancel(cancel_job, job_id, namespace, token)
            return ExecutionStatus.FAILED

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launch a step as a HuggingFace Job (legacy synchronous API).

        This is a compatibility wrapper that calls ``submit`` followed
        by ``wait``. New code should use ``submit`` / ``get_status`` /
        ``cancel`` directly.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables for the step.

        Raises:
            RuntimeError: If the job fails or is canceled.
        """
        self.submit(info, entrypoint_command, environment)
        status = self.wait(info.step_run)
        if not status.is_successful:
            try:
                self.cancel(info.step_run)
            except Exception:
                logger.debug(
                    "Failed to cancel HF Job after failure.",
                    exc_info=True,
                )
            raise RuntimeError(f"HuggingFace Job failed with status: {status}")

    def _get_job_identity(
        self, step_run: "StepRunResponse"
    ) -> Tuple[str, Optional[str]]:
        """Recover HF Job identity from step run metadata.

        Args:
            step_run: The step run containing persisted metadata.

        Returns:
            A tuple of (job_id, namespace).

        Raises:
            RuntimeError: If the job ID metadata key is missing.
        """
        metadata = step_run.run_metadata
        job_id = metadata.get(STEP_JOB_NAME_METADATA_KEY) or metadata.get(
            METADATA_ORCHESTRATOR_RUN_ID
        )
        if not job_id:
            raise RuntimeError(
                f"Cannot find HuggingFace Job ID in step run metadata. "
                f"Expected key '{STEP_JOB_NAME_METADATA_KEY}' or "
                f"'{METADATA_ORCHESTRATOR_RUN_ID}'. Available keys: "
                f"{list(metadata.keys())}"
            )
        namespace = metadata.get(_HF_JOB_NAMESPACE_METADATA_KEY)
        return str(job_id), str(namespace) if namespace else None

    @staticmethod
    def _best_effort_cancel(
        cancel_fn: Any,
        job_id: str,
        namespace: Optional[str],
        token: str,
    ) -> None:
        """Attempt to cancel a remote HF Job, suppressing errors.

        Args:
            cancel_fn: The huggingface_hub cancel_job callable.
            job_id: The HF Job ID.
            namespace: The HF namespace.
            token: The HF API token.
        """
        try:
            cancel_fn(job_id=job_id, namespace=namespace, token=token)
            logger.info("HuggingFace Job %s cancel request sent.", job_id)
        except Exception:
            logger.debug(
                "Failed to cancel HuggingFace Job %s.",
                job_id,
                exc_info=True,
            )
