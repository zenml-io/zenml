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
"""Amazon SageMaker orchestrator flavor."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union

from pydantic import Field, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.aws import (
    AWS_RESOURCE_TYPE,
    AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR,
)
from zenml.models import ServiceConnectorRequirements
from zenml.orchestrators import BaseOrchestratorConfig
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor
from zenml.utils import deprecation_utils
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.aws.orchestrators import SagemakerOrchestrator

DEFAULT_TRAINING_INSTANCE_TYPE = "ml.m5.xlarge"
DEFAULT_PROCESSING_INSTANCE_TYPE = "ml.t3.medium"
DEFAULT_OUTPUT_DATA_S3_MODE = "EndOfJob"


class SagemakerOrchestratorSettings(BaseSettings):
    """Settings for the Sagemaker orchestrator."""

    synchronous: bool = Field(
        True,
        description="Controls whether pipeline execution blocks the client. If True, "
        "the client waits until all steps complete before returning. If False, "
        "returns immediately and executes asynchronously. Useful for long-running "
        "production pipelines where you don't want to maintain a connection",
    )

    instance_type: Optional[str] = Field(
        None,
        description="AWS EC2 instance type for step execution. Must be a valid "
        "SageMaker-supported instance type. Examples: 'ml.t3.medium' (2 vCPU, 4GB RAM), "
        "'ml.m5.xlarge' (4 vCPU, 16GB RAM), 'ml.p3.2xlarge' (8 vCPU, 61GB RAM, 1 GPU). "
        "Defaults to ml.m5.xlarge for training steps or ml.t3.medium for processing steps",
    )
    execution_role: Optional[str] = Field(
        None,
        description="IAM role ARN for SageMaker step execution permissions. Must have "
        "necessary policies attached (SageMakerFullAccess, S3 access, etc.). "
        "Example: 'arn:aws:iam::123456789012:role/SageMakerExecutionRole'. "
        "If not provided, uses the default SageMaker execution role",
    )
    volume_size_in_gb: int = Field(
        30,
        description="EBS volume size in GB for step execution storage. Must be between "
        "1-16384 GB. Used for temporary files, model artifacts, and data processing. "
        "Larger volumes needed for big datasets or model training. Example: 30 for "
        "small jobs, 100+ for large ML training jobs",
    )
    max_runtime_in_seconds: int = Field(
        86400,  # 24 hours
        description="Maximum execution time in seconds before job termination. Must be "
        "between 1-432000 seconds (5 days). Used to prevent runaway jobs and control costs. "
        "Examples: 3600 (1 hour), 86400 (24 hours), 259200 (3 days). "
        "Consider your longest expected step duration",
    )
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Tags to apply to the Processor/Estimator assigned to the step. "
        "Example: {'Environment': 'Production', 'Project': 'MLOps'}",
    )
    pipeline_tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Tags to apply to the pipeline via the "
        "sagemaker.workflow.pipeline.Pipeline.create method. Example: "
        "{'Environment': 'Production', 'Project': 'MLOps'}",
    )
    keep_alive_period_in_seconds: Optional[int] = Field(
        300,  # 5 minutes
        description="The time in seconds after which the provisioned instance "
        "will be terminated if not used. This is only applicable for "
        "TrainingStep type.",
    )
    use_training_step: Optional[bool] = Field(
        None,
        description="Whether to use the TrainingStep type. It is not possible "
        "to use TrainingStep type if the `output_data_s3_uri` is set to "
        "Dict[str, str] or if the `output_data_s3_mode` != 'EndOfJob'.",
    )

    processor_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments that are directly passed to the SageMaker "
        "Processor for a specific step, allowing for overriding the default "
        "settings provided when configuring the component. Example: "
        "{'instance_count': 2, 'base_job_name': 'my-processing-job'}",
    )
    estimator_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments that are directly passed to the SageMaker "
        "Estimator for a specific step, allowing for overriding the default "
        "settings provided when configuring the component. Example: "
        "{'train_instance_count': 2, 'train_max_run': 3600}",
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to pass to the container. "
        "Example: {'LOG_LEVEL': 'INFO', 'DEBUG_MODE': 'False'}",
    )

    input_data_s3_mode: str = Field(
        "File",
        description="How data is made available to the container. "
        "Two possible input modes: File, Pipe.",
    )
    input_data_s3_uri: Optional[Union[str, Dict[str, str]]] = Field(
        default=None,
        union_mode="left_to_right",
        description="S3 URI where data is located if not locally. Example string: "
        "'s3://my-bucket/my-data/train'. Example dict: "
        "{'training': 's3://bucket/train', 'validation': 's3://bucket/val'}",
    )

    output_data_s3_mode: str = Field(
        DEFAULT_OUTPUT_DATA_S3_MODE,
        description="How data is uploaded to the S3 bucket. "
        "Two possible output modes: EndOfJob, Continuous.",
    )
    output_data_s3_uri: Optional[Union[str, Dict[str, str]]] = Field(
        default=None,
        union_mode="left_to_right",
        description="S3 URI where data is uploaded after or during processing run. "
        "Example string: 's3://my-bucket/my-data/output'. Example dict: "
        "{'output_one': 's3://bucket/out1', 'output_two': 's3://bucket/out2'}",
    )
    processor_role: Optional[str] = Field(
        None,
        description="DEPRECATED: use `execution_role` instead. "
        "The IAM role to use for the step execution.",
    )
    processor_tags: Optional[Dict[str, str]] = Field(
        None,
        description="DEPRECATED: use `tags` instead. "
        "Tags to apply to the Processor assigned to the step.",
    )
    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        ("processor_role", "execution_role"), ("processor_tags", "tags")
    )

    @model_validator(mode="before")
    def validate_model(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if model is configured correctly.

        Args:
            data: The model data.

        Returns:
            The validated model data.

        Raises:
            ValueError: If the model is configured incorrectly.
        """
        use_training_step = data.get("use_training_step", True)
        output_data_s3_uri = data.get("output_data_s3_uri", None)
        output_data_s3_mode = data.get(
            "output_data_s3_mode", DEFAULT_OUTPUT_DATA_S3_MODE
        )
        if use_training_step and (
            isinstance(output_data_s3_uri, dict)
            or (
                isinstance(output_data_s3_uri, str)
                and (output_data_s3_mode != DEFAULT_OUTPUT_DATA_S3_MODE)
            )
        ):
            raise ValueError(
                "`use_training_step=True` is not supported when `output_data_s3_uri` is a dict or "
                f"when `output_data_s3_mode` is not '{DEFAULT_OUTPUT_DATA_S3_MODE}'."
            )
        instance_type = data.get("instance_type", None)
        if instance_type is None:
            if use_training_step:
                data["instance_type"] = DEFAULT_TRAINING_INSTANCE_TYPE
            else:
                data["instance_type"] = DEFAULT_PROCESSING_INSTANCE_TYPE
        return data


class SagemakerOrchestratorConfig(
    BaseOrchestratorConfig, SagemakerOrchestratorSettings
):
    """Config for the Sagemaker orchestrator.

    There are three ways to authenticate to AWS:
    - By connecting a `ServiceConnector` to the orchestrator,
    - By configuring explicit AWS credentials `aws_access_key_id`,
        `aws_secret_access_key`, and optional `aws_auth_role_arn`,
    - If none of the above are provided, unspecified credentials will be
        loaded from the default AWS config.
    """

    execution_role: str = Field(
        ..., description="The IAM role ARN to use for the pipeline."
    )
    scheduler_role: Optional[str] = Field(
        None,
        description="The ARN of the IAM role that will be assumed by "
        "the EventBridge service to launch Sagemaker pipelines. "
        "Required for scheduled pipelines.",
    )
    aws_access_key_id: Optional[str] = SecretField(
        default=None,
        description="The AWS access key ID to use to authenticate to AWS. "
        "If not provided, the value from the default AWS config will be used.",
    )
    aws_secret_access_key: Optional[str] = SecretField(
        default=None,
        description="The AWS secret access key to use to authenticate to AWS. "
        "If not provided, the value from the default AWS config will be used.",
    )
    aws_profile: Optional[str] = Field(
        None,
        description="The AWS profile to use for authentication if not using "
        "service connectors or explicit credentials. If not provided, the "
        "default profile will be used.",
    )
    aws_auth_role_arn: Optional[str] = Field(
        None,
        description="The ARN of an intermediate IAM role to assume when "
        "authenticating to AWS.",
    )
    region: Optional[str] = Field(
        None,
        description="The AWS region where the processing job will be run. "
        "If not provided, the value from the default AWS config will be used.",
    )
    bucket: Optional[str] = Field(
        None,
        description="Name of the S3 bucket to use for storing artifacts "
        "from the job run. If not provided, a default bucket will be created "
        "based on the following format: 'sagemaker-{region}-{aws-account-id}'.",
    )

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return self.synchronous

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator is schedulable or not.

        Returns:
            Whether the orchestrator is schedulable or not.
        """
        return True


class SagemakerOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the Sagemaker orchestrator."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor.

        Returns:
            Requirements for compatible service connectors, if a service
            connector is required for this flavor.
        """
        return ServiceConnectorRequirements(resource_type=AWS_RESOURCE_TYPE)

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/sagemaker.png"

    @property
    def config_class(self) -> Type[SagemakerOrchestratorConfig]:
        """Returns SagemakerOrchestratorConfig config class.

        Returns:
            The config class.
        """
        return SagemakerOrchestratorConfig

    @property
    def implementation_class(self) -> Type["SagemakerOrchestrator"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.aws.orchestrators import SagemakerOrchestrator

        return SagemakerOrchestrator
