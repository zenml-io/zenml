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

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

import boto3
import sagemaker

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.aws.flavors.sagemaker_step_operator_flavor import (
    SagemakerStepOperatorConfig,
    SagemakerStepOperatorSettings,
)
from zenml.integrations.aws.step_operators.sagemaker_step_operator_entrypoint_config import (
    SAGEMAKER_ESTIMATOR_STEP_ENV_VAR_SIZE_LIMIT,
    SagemakerEntrypointConfiguration,
)
from zenml.logger import get_logger
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
    from zenml.models import PipelineDeploymentBase

logger = get_logger(__name__)

SAGEMAKER_DOCKER_IMAGE_KEY = "sagemaker_step_operator"
_ENTRYPOINT_ENV_VARIABLE = "__ZENML_ENTRYPOINT"


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
        return SagemakerEntrypointConfiguration

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
        self, deployment: "PipelineDeploymentBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            deployment: The pipeline deployment for which to get the builds.

        Returns:
            The required Docker builds.
        """
        builds = []
        for step_name, step in deployment.step_configurations.items():
            if step.config.step_operator == self.name:
                build = BuildConfiguration(
                    key=SAGEMAKER_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                    entrypoint=f"${_ENTRYPOINT_ENV_VARIABLE}",
                )
                builds.append(build)

        return builds

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launches a step on SageMaker.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.

        Raises:
            RuntimeError: If the connector returns an object that is not a
                `boto3.Session`.
        """
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

        # Sagemaker does not allow environment variables longer than 512
        # characters to be passed to Estimator steps. If an environment variable
        # is longer than 512 characters, we split it into multiple environment
        # variables (chunks) and re-construct it on the other side using the
        # custom entrypoint configuration.
        split_environment_variables(
            env=environment,
            size_limit=SAGEMAKER_ESTIMATOR_STEP_ENV_VAR_SIZE_LIMIT,
        )

        image_name = info.get_image(key=SAGEMAKER_DOCKER_IMAGE_KEY)
        environment[_ENTRYPOINT_ENV_VARIABLE] = " ".join(entrypoint_command)

        # Get and default fill SageMaker estimator arguments for full ZenML support
        estimator_args = settings.estimator_args

        # Get authenticated session
        # Option 1: Service connector
        boto_session: boto3.Session
        if connector := self.get_connector():
            boto_session = connector.connect()
            if not isinstance(boto_session, boto3.Session):
                raise RuntimeError(
                    f"Expected to receive a `boto3.Session` object from the "
                    f"linked connector, but got type `{type(boto_session)}`."
                )
        # Option 2: Implicit configuration
        else:
            boto_session = boto3.Session()

        session = sagemaker.Session(
            boto_session=boto_session, default_bucket=self.config.bucket
        )

        estimator_args.setdefault(
            "instance_type", settings.instance_type or "ml.m5.large"
        )

        # Convert environment to a dict of strings
        environment = {key: str(value) for key, value in environment.items()}

        estimator_args["environment"] = environment
        estimator_args["instance_count"] = 1
        estimator_args["sagemaker_session"] = session

        # Create Estimator
        estimator = sagemaker.estimator.Estimator(
            image_name, self.config.role, **estimator_args
        )

        # SageMaker allows 63 characters at maximum for job name - ZenML uses 60 for safety margin.
        step_name = Client().get_run_step(info.step_run_id).name
        training_job_name = f"{info.pipeline.name}-{step_name}"[:55]
        suffix = random_str(4)
        unique_training_job_name = f"{training_job_name}-{suffix}"

        # Sagemaker doesn't allow any underscores in job/experiment/trial names
        sanitized_training_job_name = unique_training_job_name.replace(
            "_", "-"
        )

        # Construct training input object, if necessary
        inputs = None

        if isinstance(settings.input_data_s3_uri, str):
            inputs = sagemaker.inputs.TrainingInput(
                s3_data=settings.input_data_s3_uri
            )
        elif isinstance(settings.input_data_s3_uri, dict):
            inputs = {}
            for channel, s3_uri in settings.input_data_s3_uri.items():
                inputs[channel] = sagemaker.inputs.TrainingInput(
                    s3_data=s3_uri
                )

        experiment_config = {}
        if settings.experiment_name:
            experiment_config = {
                "ExperimentName": settings.experiment_name,
                "TrialName": sanitized_training_job_name,
            }
        info.force_write_logs()
        estimator.fit(
            wait=True,
            inputs=inputs,
            experiment_config=experiment_config,
            job_name=sanitized_training_job_name,
        )
