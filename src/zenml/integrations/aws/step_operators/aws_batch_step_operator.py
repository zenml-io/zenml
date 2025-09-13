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
import math
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Literal,
    cast,
)
from pydantic import BaseModel
import boto3

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.aws.flavors.aws_batch_step_operator_flavor import (
    AWSBatchStepOperatorConfig,
    AWSBatchStepOperatorSettings,
)
from zenml.integrations.aws.step_operators.aws_batch_step_operator_entrypoint_config import (
    AWSBatchEntrypointConfiguration,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator
from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)
from zenml.utils.string_utils import random_str

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config import ResourceSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineDeploymentBase

logger = get_logger(__name__)

BATCH_DOCKER_IMAGE_KEY = "aws_batch_step_operator"
_ENTRYPOINT_ENV_VARIABLE = "__ZENML_ENTRYPOINT"

class AWSBatchJobDefinitionContainerProperties(BaseModel):
    """An AWS Batch job subconfiguration model for a container specification."""
    image: str
    command: List[str]
    jobRoleArn: str
    executionRoleArn: str
    environment: List[Dict[str,str]] = [] # keys: 'name','value'
    instanceType: str
    resourceRequirements: List[Dict[str,str]] = [] # keys: 'value','type', with type one of 'GPU','VCPU','MEMORY'
    secrets: List[Dict[str,str]] = [] # keys: 'name','value'

class AWSBatchJobDefinitionNodePropertiesNodeRangeProperty(BaseModel):
    """An AWS Batch job subconfiguration model for a node in a multinode job
    specifications.
    
    Note: We include this class for completeness sake to make it easier to add
    multinode support later for now.
    """
    targetNodes: str
    container: AWSBatchJobDefinitionContainerProperties

class AWSBatchJobDefinitionNodeProperties(BaseModel):
    """An AWS Batch job subconfiguration model for multinode job specifications.
    
    Note: We include this class for completeness sake to make it easier to add
    multinode support later for now, we'll set defaults to intuitively 
    represent the only supported exeuction type ('container'); in reality AWS
     Batch will ignore this config.
    """
    numNodes: int = 1
    mainNode: int = 0
    nodeRangeProperties: List[
        AWSBatchJobDefinitionNodePropertiesNodeRangeProperty
    ] = []

class AWSBatchJobDefinitionRetryStrategy(BaseModel):
    """An AWS Batch job subconfiguration model for retry specifications."""
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

class AWSBatchJobDefinition(BaseModel):
    """A utility to validate AWS Batch job descriptions.
    
    Defaults fall into two categories:
    - reasonable default values
    - aligning the job description to be a valid 'container' type configuration,
        as multinode jobs are not supported yet."""
    
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
    """Step operator to run a step on AWS Batch.

    This class defines code that builds an image with the ZenML entrypoint
    to run using AWS Batch.
    """

    @property
    def config(self) -> AWSBatchStepOperatorConfig:
        """Returns the `AWSBatchStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(AWSBatchStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the AWS Batch step operator.

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
    
    @staticmethod
    def map_environment(environment: Dict[str,str]) -> List[Dict[str,str]]:
        """Utility to map the {name:value} environment to the
        [{"name":name,"value":value},] convention used in the AWS Batch job
        definition spec.

        Args:
            environment (Dict[str,str]): The step's environment variable 
            specification

        Returns:
            List[Dict[str,str]]: The mapped environment variable specification
        """

        return [
            {"name":k,"value":v} for k,v in environment.items()
        ]
    
    @staticmethod
    def map_resource_settings(resource_settings: "ResourceSettings") -> List[Dict[str,str]]:
        """Utility to map the resource_settings to the resource convention used
        in the AWS Batch Job definition spec.

        Args:
            resource_settings (ResourceSettings): The step's resource settings.

        Returns:
            List[Dict[str,str]]: The mapped resource settings.
        """
        mapped_resource_settings = []

        if resource_settings.empty:
            return mapped_resource_settings
        else:

            if resource_settings.cpu_count is not None:

                cpu_count_int = math.ceil(resource_settings.cpu_count)

                if cpu_count_int != resource_settings.cpu_count:
                    logger.info(f"AWS Batch only accepts int type cpu resource requirements. Converted {resource_settings.cpu_count} to {cpu_count_int}")

                mapped_resource_settings.append(
                    {
                        "value": str(cpu_count_int),
                        "type": 'VCPU'
                    }
                )

            if resource_settings.gpu_count is not None:
                mapped_resource_settings.append(
                    {
                        "value": str(resource_settings.gpu_count),
                        "type": 'GPU'
                    }
                )

            if resource_settings.get_memory() is not None:
                mapped_resource_settings.append(
                    {
                        "value": str(int(resource_settings.get_memory(unit="MiB"))),
                        "type": 'MEMORY'
                    }
                )

        return mapped_resource_settings
    
    @staticmethod
    def generate_unique_batch_job_name(info: "StepRunInfo") -> str:
        """Utility to generate a unique AWS Batch job name.

        Args:
            info (StepRunInfo): The step run information.

        Returns:
            str: A unique name for the step's AWS Batch job definition
        """

        # Batch allows 63 characters at maximum for job name - ZenML uses 60 for safety margin.
        step_name = Client().get_run_step(info.step_run_id).name
        job_name = f"{info.pipeline.name}-{step_name}"[:55]
        suffix = random_str(4)
        return f"{job_name}-{suffix}"

    def generate_job_definition(self, info: "StepRunInfo", entrypoint_command: List[str], environment: Dict[str,str]) -> AWSBatchJobDefinition:
        """Utility to map zenml internal configurations to a valid AWS Batch 
        job definition."""
        
        image_name = info.get_image(key=BATCH_DOCKER_IMAGE_KEY)

        resource_settings = info.config.resource_settings
        step_settings = cast(AWSBatchStepOperatorSettings, self.get_settings(info))

        job_name = self.generate_unique_batch_job_name(info)

        return AWSBatchJobDefinition(
            jobDefinitionName=job_name,
            containerProperties=AWSBatchJobDefinitionContainerProperties(
                executionRoleArn=self.config.execution_role,
                jobRoleArn=self.config.job_role,
                image=image_name,
                command=entrypoint_command,
                environment=self.map_environment(environment),
                instanceType=step_settings.instance_type,
                resourceRequirements=self.map_resource_settings(resource_settings),
            ),
            timeout={'attemptDurationSeconds':step_settings.timeout_seconds},
            # type: Literal['container','multinode'] = 'container' # we dont support multinode type in this version
            # parameters: Dict[str,str] = {}
            # schedulingPriority: int = 0 # ignored in FIFO queues
            # nodeProperties: AWSBatchJobDefinitionNodeProperties = AWSBatchJobDefinitionNodeProperties(
            #     numNodes=1,mainNode=0,nodeRangeProperties=[]) # we'll focus on container mode for now - let's add multinode support later, as that will most likely require network configuration support as well 
            # retryStrategy: AWSBatchJobDefinitionRetryStrategy = AWSBatchJobDefinitionRetryStrategy()
            # propagateTags: bool = False
            # tags: Dict[str,str] = {}
            # platformCapabilities: Literal['EC2','FARGATE'] = "EC2"
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

        job_definition = self.generate_job_definition(info, entrypoint_command, environment)

        batch = boto3.client('batch')

        response = batch.register_job_definition(
            **job_definition.model_dump()
        )

        job_definition_name = response['jobDefinitionName']

        response = batch.submit_job(
            jobName=job_definition.jobDefinitionName,
            jobQueue=self.config.job_queue_name,
            jobDefinition=job_definition_name,
        )

        job_id = response['jobId']

        while True:
            response = batch.describe_jobs(jobs=[job_id])
            status = response['jobs'][0]['status']
            if status in ['SUCCEEDED', 'FAILED']:
                break
            time.sleep(10)
            logger.info(f'Job completed with status {status}')