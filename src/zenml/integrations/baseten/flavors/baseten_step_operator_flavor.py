#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Baseten step operator flavor."""

from typing import TYPE_CHECKING, Dict, Optional, Type

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.integrations.baseten import BASETEN_STEP_OPERATOR_FLAVOR
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor
from zenml.utils.secret_utils import PlainSerializedSecretStr

if TYPE_CHECKING:
    from zenml.integrations.baseten.step_operators import BasetenStepOperator


class BasetenStepOperatorSettings(BaseSettings):
    """Per-step settings for the Baseten step operator."""

    accelerator: str = Field(
        "H100",
        description="GPU accelerator type for each node. Must be a Baseten "
        "training accelerator. Examples: 'H100', 'H200'. Combine with "
        "ResourceSettings.gpu_count to set the number of GPUs per node",
    )
    node_count: int = Field(
        1,
        ge=1,
        description="Number of nodes to provision for the job. Values above 1 "
        "run multi-node distributed training and require a CommandStep that "
        "owns its distributed launch. Examples: 1 (single node), 4 (four "
        "nodes). Keep at 1 for regular Python-function steps",
    )
    cpu_count: Optional[int] = Field(
        None,
        description="vCPUs to request per node. Defaults to the Baseten "
        "default when unset. Examples: 4, 16",
    )
    memory: Optional[str] = Field(
        None,
        description="Memory to request per node as a Kubernetes-style "
        "quantity. Defaults to the Baseten default when unset. Examples: "
        "'16Gi', '64Gi'",
    )
    secrets: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of environment variable name to the name of a "
        "pre-existing Baseten secret. Route sensitive values (tokens, "
        "credentials) here so they are referenced rather than inlined into "
        "the job config. Example: {'HF_TOKEN': 'hf-access-token'}",
    )


class BasetenStepOperatorConfig(BaseStepOperatorConfig):
    """Configuration for the Baseten step operator."""

    api_key: PlainSerializedSecretStr = Field(
        description="Baseten API key used to submit and manage training jobs. "
        "Create one in the Baseten workspace settings. Supports "
        "{{secret.key}} references",
    )
    project: str = Field(
        description="Baseten training project name that submitted jobs are "
        "grouped under. Created automatically if it does not exist. Example: "
        "'zenml-training'",
    )
    registry_auth_secret: Optional[str] = Field(
        default=None,
        description="Name of a pre-existing Baseten secret holding container "
        "registry credentials in 'username:password' format, used to pull the "
        "step image from a private registry. Leave unset for public images. "
        "Example: 'gcr-pull-credentials'",
    )

    @property
    def is_remote(self) -> bool:
        """Whether the step operator runs steps remotely.

        Returns:
            True; Baseten training jobs always run in Baseten's cloud.
        """
        return True


class BasetenStepOperatorFlavor(BaseStepOperatorFlavor):
    """Baseten step operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return BASETEN_STEP_OPERATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/baseten.png"

    @property
    def config_class(self) -> Type[BasetenStepOperatorConfig]:
        """Returns the config class for this flavor.

        Returns:
            The config class.
        """
        return BasetenStepOperatorConfig

    @property
    def implementation_class(self) -> Type["BasetenStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.baseten.step_operators import (
            BasetenStepOperator,
        )

        return BasetenStepOperator
