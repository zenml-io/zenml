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
    """Settings for the Baseten step operator."""

    accelerator: str = Field(
        "H100",
        description="GPU accelerator type for each node, e.g. 'H100' or "
        "'H200'. The number of GPUs per node comes from "
        "ResourceSettings.gpu_count",
    )
    node_count: int = Field(
        1,
        ge=1,
        description="Number of nodes to provision. Values above 1 run "
        "multi-node distributed training and require a CommandStep that owns "
        "its distributed launch",
    )
    secrets: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of environment variable name to the name of a "
        "pre-existing Baseten secret, so sensitive values are referenced "
        "rather than inlined into the job config",
    )
    enable_cache: bool = Field(
        False,
        description="Mount Baseten's persistent training cache so datasets and "
        "weights downloaded by the job survive across runs. See "
        "https://docs.baseten.co/training/loading",
    )
    cache_enable_legacy_hf_mount: bool = Field(
        False,
        description="Also mount the legacy Hugging Face cache location so code "
        "using the default HF cache path reuses downloads across runs. Only "
        "applies when enable_cache is True",
    )
    cache_require_affinity: bool = Field(
        True,
        description="Require the job to schedule onto nodes that already hold "
        "the training cache. Set False to let it run on any node (e.g. across "
        "different GPU types) at the cost of cache warmth. Only applies when "
        "enable_cache is True",
    )
    enable_checkpointing: bool = Field(
        False,
        description="Persist checkpoints written to the Baseten checkpoint "
        "directory ($BT_CHECKPOINT_DIR) so they survive the job and are "
        "deployable",
    )


class BasetenStepOperatorConfig(BaseStepOperatorConfig):
    """Configuration for the Baseten step operator."""

    api_key: PlainSerializedSecretStr = Field(
        description="Baseten API key used to submit and manage training jobs, "
        "created in the Baseten workspace settings",
    )
    project: str = Field(
        description="Baseten training project name that submitted jobs are "
        "grouped under. Created automatically if it does not exist",
    )
    registry_auth_secret: Optional[str] = Field(
        default=None,
        description="Name of a pre-existing Baseten secret holding container "
        "registry credentials in 'username:password' format, used to pull the "
        "step image from a private registry. If unset, the active stack's "
        "container registry credentials are upserted into a managed secret "
        "automatically (public registries need none)",
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
