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
"""Vertex experiment tracker flavor."""

import re
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union

from google.cloud.aiplatform import utils
from pydantic import field_validator

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTrackerConfig,
    BaseExperimentTrackerFlavor,
)
from zenml.integrations.gcp import GCP_VERTEX_EXPERIMENT_TRACKER_FLAVOR
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.gcp.experiment_trackers import (
        VertexExperimentTracker,
    )


class VertexExperimentTrackerSettings(BaseSettings):
    """Settings for the VertexAI experiment tracker.

    Attributes:
        experiment: The VertexAI experiment name.
        experiment_tensorboard: The VertexAI experiment tensorboard.
    """

    experiment: Optional[str] = None
    experiment_tensorboard: Optional[Union[str, bool]] = None

    @field_validator("experiment", mode="before")
    def _validate_experiment(cls, value: str) -> str:
        """Validates the experiment name matches the regex [a-z0-9][a-z0-9-]{0,127}.

        Args:
            value: The experiment.

        Returns:
            The experiment.
        """
        if value and not re.match(r"^[a-z0-9][a-z0-9-]{0,127}$", value):
            raise ValueError(
                "Experiment name must match regex [a-z0-9][a-z0-9-]{0,127}"
            )
        return value


class VertexExperimentTrackerConfig(
    BaseExperimentTrackerConfig,
    GoogleCredentialsConfigMixin,
    VertexExperimentTrackerSettings,
):
    """Config for the VertexAI experiment tracker.

    Attributes:
        location: Optional. The default location to use when making API calls. If not
            set defaults to us-central-1.
        staging_bucket: Optional. The default staging bucket to use to stage artifacts
            when making API calls. In the form gs://...
        network:
            Optional. The full name of the Compute Engine network to which jobs
            and resources should be peered. E.g. "projects/12345/global/networks/myVPC".
            Private services access must already be configured for the network.
            If specified, all eligible jobs and resources created will be peered
            with this VPC.
        service_account:
            Optional. The service account used to launch jobs and deploy models.
            Jobs that use service_account: BatchPredictionJob, CustomJob,
            PipelineJob, HyperparameterTuningJob, CustomTrainingJob,
            CustomPythonPackageTrainingJob, CustomContainerTrainingJob,
            ModelEvaluationJob.
        encryption_spec_key_name:
            Optional. The Cloud KMS resource identifier of the customer
            managed encryption key used to protect a resource. Has the
            form:
            ``projects/my-project/locations/my-region/keyRings/my-kr/cryptoKeys/my-key``.
            The key needs to be in the same region as where the compute
            resource is created.
        api_endpoint (str):
                Optional. The desired API endpoint,
                e.g., us-central1-aiplatform.googleapis.com
        api_key (str):
            Optional. The API key to use for service calls.
            NOTE: Not all services support API keys.
        api_transport (str):
            Optional. The transport method which is either 'grpc' or 'rest'.
            NOTE: "rest" transport functionality is currently in a
            beta state (preview).
        request_metadata:
            Optional. Additional gRPC metadata to send with every client request.
    """
    location: Optional[str] = None
    staging_bucket: Optional[str] = None
    network: Optional[str] = None
    service_account: Optional[str] = SecretField(default=None)
    encryption_spec_key_name: Optional[str] = SecretField(default=None)
    api_endpoint: Optional[str] = SecretField(default=None)
    request_metadata: Optional[Dict[str, Any]] = None
    api_transport: Optional[str] = None
    request_metadata: Optional[dict] = None

    @field_validator("location", mode="before")
    def _validate_experiment(cls, value: str) -> str:
        """Validates if provided location is valid.

        Args:
            value: The gcp location name.

        Returns:
            The location name.
        """
        utils.validate_region(value)
        return value


class VertexExperimentTrackerFlavor(BaseExperimentTrackerFlavor):
    """Flavor for the VertexAI experiment tracker."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return GCP_VERTEX_EXPERIMENT_TRACKER_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        # TODO: replace with a proper logo
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/vertexai.png"

    @property
    def config_class(self) -> Type[VertexExperimentTrackerConfig]:
        """Returns `VertexExperimentTrackerConfig` config class.

        Returns:
            The config class.
        """
        return VertexExperimentTrackerConfig

    @property
    def implementation_class(self) -> Type["VertexExperimentTracker"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.gcp.experiment_trackers import (
            VertexExperimentTracker,
        )

        return VertexExperimentTracker
