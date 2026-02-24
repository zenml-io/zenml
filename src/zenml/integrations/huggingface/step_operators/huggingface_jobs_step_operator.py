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
from zenml.metadata.metadata_types import Uri
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


def _check_hf_jobs_availability() -> None:
    """Verify that the installed huggingface_hub supports the Jobs API.

    Raises:
        RuntimeError: If the Jobs API is not available.
    """
    try:
        from huggingface_hub import run_job  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "The installed version of `huggingface_hub` does not support "
            "the Jobs API. Please upgrade: "
            "`pip install 'huggingface_hub>=0.30.0'`"
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
            return cached
    except Exception:
        pass

    raise RuntimeError(
        "No Hugging Face token found. Please either: "
        "(1) set the `token` field on the step operator component, "
        "(2) set the HF_TOKEN environment variable, or "
        "(3) run `huggingface-cli login`."
    )


def split_environment(
    environment: Dict[str, str],
    pass_as_secrets: bool,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Split environment variables into plain env and HF encrypted secrets.

    When pass_as_secrets is True, all variables go to secrets (encrypted
    server-side by HF). Otherwise they are sent as plain env vars.

    Args:
        environment: The full environment dict from ZenML.
        pass_as_secrets: Whether to route vars through HF secrets.

    Returns:
        A tuple of (plain_env, secrets).
    """
    if pass_as_secrets:
        return {}, dict(environment)
    return dict(environment), {}


class HuggingFaceJobsStepOperator(BaseStepOperator):
    """Step operator that runs individual steps as Hugging Face Jobs.

    HF Jobs execute Docker containers on Hugging Face infrastructure,
    supporting both CPU and GPU hardware flavors. This operator submits
    the ZenML step entrypoint command as a Job, polls until completion,
    and streams logs back to ZenML.

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
        from huggingface_hub._space_api import SpaceHardware

        settings = cast(
            HuggingFaceJobsStepOperatorSettings, self.get_settings(info)
        )

        image = info.get_image(key=HUGGINGFACE_JOBS_DOCKER_IMAGE_KEY)
        token = _resolve_token(self.config)

        hardware_flavor_str = (
            settings.hardware_flavor or self.config.hardware_flavor
        )
        hardware_flavor = (
            SpaceHardware(hardware_flavor_str) if hardware_flavor_str else None
        )
        timeout = settings.timeout or self.config.timeout
        namespace = settings.namespace or self.config.namespace

        plain_env, secrets = split_environment(
            environment, self.config.pass_env_as_secrets
        )

        # Provide the HF token inside the job so user code can interact
        # with the Hub (push/pull models, datasets, etc.)
        secrets.setdefault("HF_TOKEN", token)

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
            step_metadata = {
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

        log_offset = 0

        try:
            while True:
                job_info = inspect_job(
                    job_id=job.id,
                    namespace=namespace,
                    token=token,
                )
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
            try:
                cancel_job(job_id=job.id, namespace=namespace, token=token)
                logger.info("HuggingFace Job %s cancel request sent.", job.id)
            except Exception:
                logger.warning(
                    "Failed to cancel HuggingFace Job %s.",
                    job.id,
                    exc_info=True,
                )
            raise
