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

import time
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    Literal,
    cast,
)
from pydantic import BaseModel

import boto3
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.session import Session

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.aws.flavors.batch_step_operator_flavor import (
    AWSBatchStepOperatorConfig,
    AWSBatchStepOperatorSettings,
)
from zenml.integrations.aws.step_operators.batch_step_operator_entrypoint_config import (
    BATCH_STEP_ENV_VAR_SIZE_LIMIT,
    AWSBatchEntrypointConfiguration,
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

BATCH_DOCKER_IMAGE_KEY = "batch_step_operator"
_ENTRYPOINT_ENV_VARIABLE = "__ZENML_ENTRYPOINT"

class AWSBatchJobDefinitionContainerProperties(BaseModel):
    image: str
    command: List[str]
    jobRoleArn: str
    executionRoleArn: str
    environment: List[Dict[str,str]] = [] # keys: 'name','value'
    instanceType: str
    resourceRequirements: List[Dict[str,str]] = [] # keys: 'value','type', with type one of 'GPU','VCPU','MEMORY'
    secrets: List[Dict[str,str]] = [] # keys: 'name','value'

class AWSBatchJobDefinitionNodePropertiesNodeRangeProperty(BaseModel):
    targetNodes: str
    container: AWSBatchJobDefinitionContainerProperties

class AWSBatchJobDefinitionNodeProperties(BaseModel):
    # we include this class for completeness sake to make it easier
    # to add multinode support later
    # for now, we'll set defaults to intuitively represent the only supported
    # exeuction type ('container'); in reality AWS Batch will ignore this
    # config
    numNodes: int = 1
    mainNode: int = 0
    nodeRangeProperties: List[AWSBatchJobDefinitionNodePropertiesNodeRangeProperty] = []

class AWSBatchJobDefinitionRetryStrategy(BaseModel):
    attempts: int = 2
    evaluateOnExit: List[Dict[str,str]] = [
        {
            "onExitCode": "137",  # out-of-memory killed
            "action": "RETRY"
        },
        {
            "onReason": "*Host EC2*",
            "action": "RETRY"
        },
        {
            "onExitCode": "*",  # match everything else
            "action": "EXIT"
        }
    ]
            # Example:
            # {
            #     'onStatusReason': 'string',
            #     'onReason': 'string',
            #     'onExitCode': 'string',
            #     'action': 'RETRY'|'EXIT'
            # },

class AWSBatchJobDefinition(BaseModel):
    jobDefinitionName: str
    type: Literal['container','multinode'] = 'container' # we dont support multinode type in this version
    parameters: Dict[str,str] = {}
    schedulingPriority: int = 0 # ignored in FIFO queues
    containerProperties: AWSBatchJobDefinitionContainerProperties
    nodeProperties: AWSBatchJobDefinitionNodeProperties = AWSBatchJobDefinitionNodeProperties(
        numNodes=1,mainNode=0,nodeRangeProperties=[]) # we'll focus on container mode for now - let's add multinode support later, as that will most likely require network configuration support as well 
    retryStrategy: AWSBatchJobDefinitionRetryStrategy = AWSBatchJobDefinitionRetryStrategy()
    propagateTags: bool = False
    timeout: Dict[str,int] = {'attemptDurationSeconds':60} # key 'attemptDurationSeconds'
    tags: Dict[str,str] = {}
    platformCapabilities: Literal['EC2','FARGATE'] = "EC2" #-- hardcode this to EC2, so we can use container and multinode interchangeably without worrying too much


class AWSBatchStepOperator(BaseStepOperator):
    """Step operator to run a step on Sagemaker.

    This class defines code that builds an image with the ZenML entrypoint
    to run using Sagemaker's Estimator.
    """

    @property
    def config(self) -> AWSBatchStepOperatorConfig:
        """Returns the `SagemakerStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(AWSBatchStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the SageMaker step operator.

        Returns:
            The settings class.
        """
        return AWSBatchStepOperatorSettings

    @property
    def entrypoint_config_class(
        self,
    ) -> Type[StepOperatorEntrypointConfiguration]:
        """Returns the entrypoint configuration class for this step operator.

        Returns:
            The entrypoint configuration class for this step operator.
        """
        return AWSBatchEntrypointConfiguration

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
                    "The Batch step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the Batch "
                    "step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Batch step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "Batch step operator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )
    

    def generate_job_definition(self, info: "StepRunInfo", entrypoint_command: List[str], environment: Dict[str,str]) -> AWSBatchJobDefinition:
        """Utility to map zenml internal configurations to a valid AWS Batch 
        job definition."""
        pass


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
            if step.config.uses_step_operator(self.name):
                build = BuildConfiguration(
                    key=BATCH_DOCKER_IMAGE_KEY,
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
        """Launches a step on AWS Batch.

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
                "the AWS Batch step operator. If you want to run this step "
                "operator on specific resources, you can do so by configuring "
                "a different instance type like this: "
                "`zenml step-operator update %s "
                "--instance_type=<INSTANCE_TYPE>`",
                self.name,
            )

        image_name = info.get_image(key=BATCH_DOCKER_IMAGE_KEY)

        settings = cast(AWSBatchStepOperatorSettings, self.get_settings(info))

        batch = boto3.client('batch')
        
        # Batch allows 63 characters at maximum for job name - ZenML uses 60 for safety margin.
        step_name = Client().get_run_step(info.step_run_id).name
        training_job_name = f"{info.pipeline.name}-{step_name}"[:55]
        suffix = random_str(4)
        unique_training_job_name = f"{training_job_name}-{suffix}"
        
        response = batch.register_job_definition(
            jobDefinitionName=unique_training_job_name,
            type='container',
            containerProperties={
                'image': image_name ,
                'command': entrypoint_command,
            }
        )

        job_definition = response['jobDefinitionName']

        response = batch.submit_job(
            jobName=unique_training_job_name,
            jobQueue=self.config.job_queue_name,
            jobDefinition=job_definition,
        )

        job_id = response['jobId']

        while True:
            response = batch.describe_jobs(jobs=[job_id])
            status = response['jobs'][0]['status']
            if status in ['SUCCEEDED', 'FAILED']:
                break
            time.sleep(10)
            logger.info(f'Job completed with status {status}')