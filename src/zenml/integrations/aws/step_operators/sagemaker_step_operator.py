#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of the Sagemaker Step Operator."""

from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)

import boto3
from sagemaker.core.helper.session_helper import Session
from sagemaker.core.shapes import StoppingCondition
from sagemaker.core.training.configs import Compute, InputData, SourceCode
from sagemaker.train.model_trainer import ModelTrainer

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.aws.flavors.sagemaker_step_operator_flavor import (
    SagemakerStepOperatorConfig,
    SagemakerStepOperatorSettings,
)
from zenml.integrations.aws.step_operators.sagemaker_step_operator_entrypoint_config import (
    SAGEMAKER_ESTIMATOR_STEP_ENV_VAR_SIZE_LIMIT,
    SagemakerStepOperatorEntrypointConfiguration,
)
from zenml.integrations.aws.utils import (
    convert_training_job_status,
)
from zenml.logger import get_logger
from zenml.orchestrators.publish_utils import publish_step_run_metadata
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator
from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)
from zenml.utils.env_utils import split_environment_variables
from zenml.utils.string_utils import random_str

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase, StepRunResponse

logger = get_logger(__name__)

SAGEMAKER_DOCKER_IMAGE_KEY = "sagemaker_step_operator"
_ENTRYPOINT_ENV_VARIABLE = "__ZENML_ENTRYPOINT"
STEP_JOB_NAME_METADATA_KEY = "job_name"


class SagemakerStepOperator(BaseStepOperator):
    """Step operator to run a step on Sagemaker.

    This class defines code that builds an image with the ZenML entrypoint
    to run using Sagemaker's Estimator.
    """

    @property
    def config(self) -> SagemakerStepOperatorConfig:
        """Returns the `SagemakerStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(SagemakerStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the SageMaker step operator.

        Returns:
            The settings class.
        """
        return SagemakerStepOperatorSettings

    @property
    def entrypoint_config_class(
        self,
    ) -> Type[StepOperatorEntrypointConfiguration]:
        """Returns the entrypoint configuration class for this step operator.

        Returns:
            The entrypoint configuration class for this step operator.
        """
        return SagemakerStepOperatorEntrypointConfiguration

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains a remote container
            registry and a remote artifact store.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The SageMaker step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the SageMaker "
                    "step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The SageMaker step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "SageMaker step operator."
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
        """Gets the Docker builds required for the component.

        Args:
            snapshot: The pipeline snapshot for which to get the builds.

        Returns:
            The required Docker builds.
        """
        builds = []
        for step_name, step in snapshot.step_configurations.items():
            if step.config.uses_step_operator(self.name):
                build = BuildConfiguration(
                    key=SAGEMAKER_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                    entrypoint=f"${_ENTRYPOINT_ENV_VARIABLE}",
                )
                builds.append(build)

        return builds

    def _get_sagemaker_session(self) -> Session:
        """Creates an authenticated Sagemaker session.

        Raises:
            RuntimeError: If the connector returns the wrong type for the session.

        Returns:
            The Sagemaker session.
        """
        boto_session: boto3.Session
        if connector := self.get_connector():
            boto_session = connector.connect()
            if not isinstance(boto_session, boto3.Session):
                raise RuntimeError(
                    f"Expected to receive a `boto3.Session` object from the "
                    f"linked connector, but got type `{type(boto_session)}`."
                )
        else:
            boto_session = boto3.Session()

        sm_session = Session(
            boto_session=boto_session, default_bucket=self.config.bucket
        )

        # v3 migration: Session may not always expose the legacy convenience client
        # attribute used elsewhere in this module. Keep behavior stable.
        if not hasattr(sm_session, "sagemaker_client"):
            setattr(
                sm_session,
                "sagemaker_client",
                boto_session.client("sagemaker"),
            )

        return sm_session

    @property
    def sagemaker_session(self) -> Session:
        """Returns the Sagemaker session.

        Returns:
            The Sagemaker session.
        """
        if self.connector_has_expired():
            self._sagemaker_session = None

        if self._sagemaker_session is None:
            self._sagemaker_session = self._get_sagemaker_session()
        return self._sagemaker_session

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Submits a step run to SageMaker."""
        import shlex

        if not info.config.resource_settings.empty:
            logger.warning(
                "Specifying custom step resources is not supported for "
                "the SageMaker step operator. If you want to run this step "
                "operator on specific resources, you can do so by configuring "
                "a different instance type like this: "
                "`zenml step-operator update %s "
                "--instance_type=<INSTANCE_TYPE>`",
                self.name,
            )

        settings = cast(SagemakerStepOperatorSettings, self.get_settings(info))

        if settings.environment:
            environment.update(settings.environment)

        # Preserve legacy env var size splitting behavior
        split_environment_variables(
            env=environment,
            size_limit=SAGEMAKER_ESTIMATOR_STEP_ENV_VAR_SIZE_LIMIT,
        )

        image_name = info.get_image(key=SAGEMAKER_DOCKER_IMAGE_KEY)
        environment[_ENTRYPOINT_ENV_VARIABLE] = " ".join(entrypoint_command)
        environment = {key: str(value) for key, value in environment.items()}

        # Build deterministic-ish job name (same as before)
        step_name = Client().get_run_step(info.step_run_id).name
        training_job_name = f"{info.pipeline.name}-{step_name}"[:55]
        suffix = random_str(4)
        unique_training_job_name = f"{training_job_name}-{suffix}"
        sanitized_training_job_name = unique_training_job_name.replace(
            "_", "-"
        )

        # Inputs: preserve “string or dict-of-channels” behavior
        input_data_config = None
        if isinstance(settings.input_data_s3_uri, str):
            input_data_config = [
                InputData(
                    channel_name="training",
                    data_source=settings.input_data_s3_uri,
                )
            ]
        elif isinstance(settings.input_data_s3_uri, dict):
            input_data_config = [
                InputData(channel_name=channel, data_source=s3_uri)
                for channel, s3_uri in settings.input_data_s3_uri.items()
            ]

        # Experiment config (same behavior)
        experiment_config = None
        if settings.experiment_name:
            experiment_config = {
                "ExperimentName": settings.experiment_name,
                "TrialName": sanitized_training_job_name,
            }

        # Preserve logging behavior
        info.force_write_logs()

        estimator_args = settings.estimator_args
        instance_type = (
            estimator_args.get("instance_type")
            or settings.instance_type
            or "ml.m5.large"
        )

        compute_kwargs = dict(
            instance_type=instance_type,
            instance_count=1,
        )

        # volume size: only set if present (avoid passing None into strict schemas)
        volume_size = estimator_args.get("volume_size") or estimator_args.get(
            "volume_size_in_gb"
        )
        if volume_size is not None:
            compute_kwargs["volume_size_in_gb"] = int(volume_size)

        compute = Compute(**compute_kwargs)

        stopping_condition = None
        max_run = estimator_args.get("max_run") or estimator_args.get(
            "max_runtime_in_seconds"
        )
        if max_run is not None:
            stopping_condition = StoppingCondition(
                max_runtime_in_seconds=int(max_run)
            )

        # SourceCode.command is a STRING in your build
        source_code = SourceCode(command=shlex.join(entrypoint_command))

        trainer_kwargs = dict(
            training_image=image_name,
            role=self.config.role,
            sagemaker_session=self.sagemaker_session,
            environment=environment,
            tags=(
                [{"Key": k, "Value": v} for k, v in settings.tags.items()]
                if settings.tags
                else None
            ),
            # Keep naming intent: base name used by SageMaker when generating job name
            base_job_name=sanitized_training_job_name,
            compute=compute,
            source_code=source_code,
        )
        if stopping_condition is not None:
            trainer_kwargs["stopping_condition"] = stopping_condition

        trainer = ModelTrainer(**trainer_kwargs)

        # ---- v3 migration: keep train() call minimal ----
        train_kwargs = dict(
            input_data_config=input_data_config,
            wait=False,
            logs=False,
        )
        if experiment_config is not None:
            train_kwargs["experiment_config"] = experiment_config

        # Prefer explicit job name if supported by your ModelTrainer.train()
        # (If your signature uses training_job_name instead of job_name, swap the key.)
        train_kwargs["job_name"] = sanitized_training_job_name

        trainer.train(**train_kwargs)

        publish_step_run_metadata(
            info.step_run_id,
            {
                self.id: {
                    STEP_JOB_NAME_METADATA_KEY: sanitized_training_job_name
                }
            },
        )
        info.step_run.run_metadata[STEP_JOB_NAME_METADATA_KEY] = (
            sanitized_training_job_name
        )

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Gets the status of a submitted step.

        Args:
            step_run: The step run.

        Returns:
            The step status.
        """
        job_name = step_run.run_metadata[STEP_JOB_NAME_METADATA_KEY]
        sagemaker_client = self.sagemaker_session.sagemaker_client

        status = sagemaker_client.describe_training_job(
            TrainingJobName=job_name
        )["TrainingJobStatus"]
        return convert_training_job_status(status)

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancels a submitted step.

        Args:
            step_run: The step run.
        """
        job_name = step_run.run_metadata[STEP_JOB_NAME_METADATA_KEY]
        sagemaker_client = self.sagemaker_session.sagemaker_client
        sagemaker_client.stop_training_job(TrainingJobName=job_name)
