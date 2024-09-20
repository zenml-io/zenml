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

from pydantic import Field

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


class SagemakerOrchestratorSettings(BaseSettings):
    """Settings for the Sagemaker orchestrator.

    Attributes:
        instance_type: The instance type to use for the processing job.
        execution_role: The IAM role to use for the step execution.
        processor_role: DEPRECATED: use `execution_role` instead.
        volume_size_in_gb: The size of the EBS volume to use for the processing
            job.
        max_runtime_in_seconds: The maximum runtime in seconds for the
            processing job.
        tags: Tags to apply to the Processor/Estimator assigned to the step.
        processor_tags: DEPRECATED: use `tags` instead.
        keep_alive_period_in_seconds: The time in seconds after which the
            provisioned instance will be terminated if not used. This is only
            applicable for TrainingStep type and it is not possible to use
            TrainingStep type if the `output_data_s3_uri` is set to Dict[str, str].
        use_training_steps_where_possible: Whether to use the TrainingStep
            type if possible. It is not possible to use TrainingStep type
            if the `output_data_s3_uri` is set to Dict[str, str] or if the
            `output_data_s3_mode` != "EndOfJob".
        processor_args: Arguments that are directly passed to the SageMaker
            Processor for a specific step, allowing for overriding the default
            settings provided when configuring the component. See
            https://sagemaker.readthedocs.io/en/stable/api/training/processing.html#sagemaker.processing.Processor
            for a full list of arguments.
            For processor_args.instance_type, check
            https://docs.aws.amazon.com/sagemaker/latest/dg/notebooks-available-instance-types.html
            for a list of available instance types.
        estimator_args: Arguments that are directly passed to the SageMaker
            Estimator for a specific step, allowing for overriding the default
            settings provided when configuring the component. See
            https://sagemaker.readthedocs.io/en/stable/api/training/estimators.html#sagemaker.estimator.Estimator
            for a full list of arguments.
            For a list of available instance types, check
            https://docs.aws.amazon.com/sagemaker/latest/dg/cmn-info-instance-types.html.
        input_data_s3_mode: How data is made available to the container.
            Two possible input modes: File, Pipe.
        input_data_s3_uri: S3 URI where data is located if not locally,
            e.g. s3://my-bucket/my-data/train. How data will be made available
            to the container is configured with input_data_s3_mode. Two possible
            input types:
                - str: S3 location where training data is saved.
                - Dict[str, str]: (ChannelName, S3Location) which represent
                    channels (e.g. training, validation, testing) where
                    specific parts of the data are saved in S3.
        output_data_s3_mode: How data is uploaded to the S3 bucket.
            Two possible output modes: EndOfJob, Continuous.
        output_data_s3_uri: S3 URI where data is uploaded after or during processing run.
            e.g. s3://my-bucket/my-data/output. How data will be made available
            to the container is configured with output_data_s3_mode. Two possible
            input types:
                - str: S3 location where data will be uploaded from a local folder
                    named /opt/ml/processing/output/data.
                - Dict[str, str]: (ChannelName, S3Location) which represent
                    channels (e.g. output_one, output_two) where
                    specific parts of the data are stored locally for S3 upload.
                    Data must be available locally in /opt/ml/processing/output/data/<ChannelName>.
    """

    instance_type: Optional[str] = None
    execution_role: Optional[str] = None
    volume_size_in_gb: int = 30
    max_runtime_in_seconds: int = 86400
    tags: Dict[str, str] = {}
    keep_alive_period_in_seconds: Optional[int] = 300  # 5 minutes
    use_training_steps_where_possible: bool = True

    processor_args: Dict[str, Any] = {}
    estimator_args: Dict[str, Any] = {}

    input_data_s3_mode: str = "File"
    input_data_s3_uri: Optional[Union[str, Dict[str, str]]] = Field(
        default=None, union_mode="left_to_right"
    )

    output_data_s3_mode: str = "EndOfJob"
    output_data_s3_uri: Optional[Union[str, Dict[str, str]]] = Field(
        default=None, union_mode="left_to_right"
    )

    processor_role: Optional[str] = None
    processor_tags: Dict[str, str] = {}
    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        "processor_role", "processor_tags"
    )


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

    Attributes:
        synchronous: If `True`, the client running a pipeline using this
            orchestrator waits until all steps finish running. If `False`,
            the client returns immediately and the pipeline is executed
            asynchronously. Defaults to `True`.
        execution_role: The IAM role ARN to use for the pipeline.
        aws_access_key_id: The AWS access key ID to use to authenticate to AWS.
            If not provided, the value from the default AWS config will be used.
        aws_secret_access_key: The AWS secret access key to use to authenticate
            to AWS. If not provided, the value from the default AWS config will
            be used.
        aws_profile: The AWS profile to use for authentication if not using
            service connectors or explicit credentials. If not provided, the
            default profile will be used.
        aws_auth_role_arn: The ARN of an intermediate IAM role to assume when
            authenticating to AWS.
        region: The AWS region where the processing job will be run. If not
            provided, the value from the default AWS config will be used.
        bucket: Name of the S3 bucket to use for storing artifacts
            from the job run. If not provided, a default bucket will be created
            based on the following format:
            "sagemaker-{region}-{aws-account-id}".
    """

    synchronous: bool = True
    execution_role: str
    aws_access_key_id: Optional[str] = SecretField(default=None)
    aws_secret_access_key: Optional[str] = SecretField(default=None)
    aws_profile: Optional[str] = None
    aws_auth_role_arn: Optional[str] = None
    region: Optional[str] = None
    bucket: Optional[str] = None

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
