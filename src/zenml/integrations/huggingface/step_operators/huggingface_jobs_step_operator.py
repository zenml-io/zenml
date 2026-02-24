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
from zenml.enums import StackComponentType
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
    from zenml.models import PipelineSnapshotBase

logger = get_logger(__name__)

HUGGINGFACE_JOBS_DOCKER_IMAGE_KEY = "huggingface_jobs_step_operator"

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

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launch a step as a HuggingFace Job.

        Submits the step's Docker image and entrypoint command to HF Jobs,
        polls until the job reaches a terminal state, and optionally streams
        logs during execution.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables for the step.

        Raises:
            RuntimeError: If the job fails, is canceled, or is deleted.
        """
        _check_hf_jobs_availability()

        from huggingface_hub import (
            JobStage,
            cancel_job,
            fetch_job_logs,
            inspect_job,
            run_job,
        )

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

        # Flush any buffered logs before submitting the remote job
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

        # Publish the HF Job URL as step run metadata so it appears
        # as a clickable link in the ZenML dashboard.
        try:
            step_metadata: Dict[str, MetadataType] = {
                METADATA_ORCHESTRATOR_RUN_ID: str(job.id),
                METADATA_ORCHESTRATOR_URL: Uri(str(job.url)),
                METADATA_ORCHESTRATOR_LOGS_URL: Uri(str(job.url)),
            }
            publish_step_run_metadata(
                step_run_id=info.step_run_id,
                step_run_metadata={self.id: step_metadata},
            )
        except Exception:
            logger.debug(
                "Failed to publish HuggingFace Job metadata.",
                exc_info=True,
            )

        # Poll until the job reaches a terminal state, with retry
        # logic for transient API errors.
        consecutive_errors = 0
        log_offset = 0

        try:
            while True:
                try:
                    job_info = inspect_job(
                        job_id=job.id,
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
                        raise RuntimeError(
                            f"Failed to poll HuggingFace Job {job.id} "
                            f"after {consecutive_errors} consecutive "
                            f"errors. Last error: {poll_err}. "
                            f"Job URL: {job.url}"
                        ) from poll_err

                    backoff = min(
                        self.config.poll_interval_seconds
                        * (2**consecutive_errors),
                        _HF_JOBS_POLL_BACKOFF_CAP_SECONDS,
                    )
                    jitter = random.uniform(0, backoff * 0.1)
                    logger.warning(
                        "Transient error polling HF Job %s "
                        "(attempt %d/%d): %s. Retrying in %.1fs.",
                        job.id,
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
                                job_id=job.id,
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
                        job.id,
                    )
                    return

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
                    raise RuntimeError(
                        f"HuggingFace Job ended with stage={stage_str}. "
                        f"Message: {message}. "
                        f"Job URL: {job.url}"
                    )

                logger.debug(
                    "HuggingFace Job %s stage: %s. Polling again in %ss.",
                    job.id,
                    stage.value if hasattr(stage, "value") else stage,
                    self.config.poll_interval_seconds,
                )
                time.sleep(self.config.poll_interval_seconds)

        except KeyboardInterrupt:
            logger.warning(
                "Interrupt received. Canceling HuggingFace Job %s...",
                job.id,
            )
            self._best_effort_cancel(cancel_job, job.id, namespace, token)
            raise
        except RuntimeError:
            # Job-terminal or poll-exhaustion errors: attempt cleanup
            logger.warning(
                "Attempting best-effort cancellation of HF Job %s...",
                job.id,
            )
            self._best_effort_cancel(cancel_job, job.id, namespace, token)
            raise
        except Exception:
            logger.warning(
                "Unexpected error while monitoring HF Job %s. "
                "Attempting best-effort cancellation...",
                job.id,
                exc_info=True,
            )
            self._best_effort_cancel(cancel_job, job.id, namespace, token)
            raise

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
