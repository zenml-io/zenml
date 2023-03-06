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

from typing import TYPE_CHECKING, List, Optional, Tuple, Type, cast

import sagemaker

from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.aws.flavors.sagemaker_step_operator_flavor import (
    SagemakerStepOperatorConfig,
    SagemakerStepOperatorSettings,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models.pipeline_deployment_models import (
        PipelineDeploymentBaseModel,
    )

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
        self, deployment: "PipelineDeploymentBaseModel"
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
    ) -> None:
        """Launches a step on SageMaker.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
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

        image_name = info.get_image(key=SAGEMAKER_DOCKER_IMAGE_KEY)
        environment = {_ENTRYPOINT_ENV_VARIABLE: " ".join(entrypoint_command)}

        settings = cast(SagemakerStepOperatorSettings, self.get_settings(info))

        session = settings.sagemaker_session or sagemaker.Session(default_bucket=self.config.bucket)
        instance_type = settings.instance_type or "ml.m5.large"
        instance_count = settings.instance_count or 1

        estimator = sagemaker.estimator.Estimator(
            image_name,
            self.config.role,
            environment=environment,
            instance_count=instance_count,
            instance_type=instance_type,
            keep_alive_period_in_seconds = settings.keep_alive_period_in_seconds,
            volume_size = settings.volume_size,
            volume_kms_key = settings.volume_kms_key,
            max_run = settings.max_run,
            input_mode = settings.input_mode,
            output_path = settings.output_path,
            output_kms_key = settings.output_kms_key,
            base_job_name = settings.base_job_name,
            sagemaker_session = session,
            hyperparameters = settings.hyperparameters,
            tags = settings.tags,
            subnets = settings.subnets,
            security_group_ids = settings.security_group_ids,
            model_uri = settings.model_uri,
            model_channel_name = settings.model_channel_name,
            metric_definitions = settings.metric_definitions,
            encrypt_inter_container_traffic = settings.encrypt_inter_container_traffic,
            use_spot_instances = settings.use_spot_instances,
            max_wait = settings.max_wait,
            checkpoint_s3_uri = settings.checkpoint_s3_uri,
            checkpoint_local_path = settings.checkpoint_local_path,
            enable_network_isolation = settings.enable_network_isolation,
            rules = settings.rules,
            debugger_hook_config = settings.debugger_hook_config,
            tensorboard_output_config = settings.tensorboard_output_config,
            enable_sagemaker_metrics = settings.enable_sagemaker_metrics,
            profiler_config = settings.profiler_config,
            disable_profiler = settings.disable_profiler,
            environment = settings.environment,
            max_retry_attempts = settings.max_retry_attempts,
            source_dir = settings.source_dir,
            git_config = settings.git_config,
            container_log_level = settings.container_log_level,
            code_location = settings.code_location,
            entry_point = settings.entry_point,
            dependencies = settings.dependencies,
            instance_groups = settings.instance_groups,
            training_repository_access_mode = settings.training_repository_access_mode,
            training_repository_credentials_provider_arn = settings.training_repository_credentials_provider_arn
        )

        # Sagemaker doesn't allow any underscores in job/experiment/trial names
        sanitized_run_name = info.run_name.replace("_", "-")

        # Construct training input object, if necessary
        inputs = None

        if isinstance(settings.input_data_s3_uri, str):
            inputs = sagemaker.inputs.TrainingInput(s3_data=settings.input_data_s3_uri)
        elif isinstance(settings.input_data_s3_uri, dict):
            inputs = {}
            for channel, s3_uri in settings.input_data_s3_uri.items():
                inputs[channel] = sagemaker.inputs.TrainingInput(s3_data=s3_uri)

        experiment_config = {}
        if settings.experiment_name:
            experiment_config = {
                "ExperimentName": settings.experiment_name,
                "TrialName": sanitized_run_name,
            }

        estimator.fit(
            wait=True,
            inputs=inputs,
            experiment_config=experiment_config,
            job_name=sanitized_run_name,
        )