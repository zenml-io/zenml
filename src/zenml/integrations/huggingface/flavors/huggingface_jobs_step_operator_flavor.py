#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Hugging Face Jobs step operator flavor."""

from typing import TYPE_CHECKING, Optional, Type, Union

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.integrations.huggingface import (
    HUGGINGFACE_JOBS_STEP_OPERATOR_FLAVOR,
)
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.huggingface.step_operators import (
        HuggingFaceJobsStepOperator,
    )


class HuggingFaceJobsStepOperatorSettings(BaseSettings):
    """Per-step runtime overrides for the HuggingFace Jobs step operator.

    These settings can be specified at the step level to override the
    component-level defaults.

    Attributes:
        hardware_flavor: HF Jobs hardware flavor for this step (e.g.,
            'cpu-basic', 'a10g-small', 'a100-large', 'h200'). Overrides the
            component default.
        timeout: Job timeout override. Accepts seconds as int/float or
            a duration string like '2h', '30m', '1d'. Overrides component
            default.
        namespace: HF namespace (user or organization) under which to run
            this job. Overrides the component default.
    """

    hardware_flavor: Optional[str] = Field(
        default=None,
        description="HF Jobs hardware flavor for step execution. Controls "
        "compute resources (CPU, GPU type and count, memory). Examples: "
        "'cpu-basic', 'a10g-small', 'a100-large', 'h200'. Passed directly to "
        "Hugging Face Jobs; see https://huggingface.co/docs/hub/jobs for "
        "available options. Overrides the component-level default.",
    )
    timeout: Optional[Union[int, float, str]] = Field(
        default=None,
        description="Maximum duration for this job before automatic "
        "termination. Accepts seconds as int/float or a string with units: "
        "'5m' (minutes), '2h' (hours), '1d' (days). Examples: 300, '30m', "
        "'2h'. Default HF timeout is 30 minutes if unset.",
    )
    namespace: Optional[str] = Field(
        default=None,
        description="Hugging Face namespace (username or organization) under "
        "which to run this job. Overrides the component default. Example: "
        "'my-org' runs the job under the 'my-org' organization account.",
    )


class HuggingFaceJobsStepOperatorConfig(
    BaseStepOperatorConfig, HuggingFaceJobsStepOperatorSettings
):
    """Configuration for the HuggingFace Jobs step operator.

    Attributes:
        token: Hugging Face API token with Jobs permissions. Required for
            Pro/Team/Enterprise accounts. Used only for HF Jobs API calls,
            not automatically injected into job containers.
        pass_env_as_secrets: If True, ZenML environment variables are sent
            as HF encrypted secrets rather than plain env vars.
    """

    token: Optional[str] = SecretField(
        default=None,
        description="Hugging Face API token for authenticating Jobs API "
        "calls. Requires a Pro, Team, or Enterprise account with Jobs access. "
        "Can reference a ZenML secret: '{{hf_secret.token}}'. Used only for "
        "HF Jobs management API calls and not automatically injected into "
        "step containers. If omitted, falls back to `huggingface_hub.get_token()` "
        "(HF_TOKEN or cached login from `hf auth login`).",
    )
    pass_env_as_secrets: bool = Field(
        default=True,
        description="Controls whether ZenML environment variables (which "
        "may contain cloud credentials) are passed as HF encrypted secrets "
        "or plain environment variables. HF secrets are encrypted server-side "
        "and not visible in job specs. Step-supplied HF tokens are always "
        "passed as encrypted secrets. Defaults to True for security.",
    )

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Returns:
            True, since HF Jobs always run on remote infrastructure.
        """
        return True


class HuggingFaceJobsStepOperatorFlavor(BaseStepOperatorFlavor):
    """Flavor for the Hugging Face Jobs step operator."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The flavor name.
        """
        return HUGGINGFACE_JOBS_STEP_OPERATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/huggingface.png"

    @property
    def config_class(self) -> Type[HuggingFaceJobsStepOperatorConfig]:
        """Returns `HuggingFaceJobsStepOperatorConfig` config class.

        Returns:
            The config class.
        """
        return HuggingFaceJobsStepOperatorConfig

    @property
    def implementation_class(self) -> Type["HuggingFaceJobsStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.huggingface.step_operators import (
            HuggingFaceJobsStepOperator,
        )

        return HuggingFaceJobsStepOperator
