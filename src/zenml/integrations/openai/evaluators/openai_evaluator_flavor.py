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
"""Config and Flavor for OpenAIEvaluator."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.evaluators.base_evaluator import (
    BaseEvaluatorConfig,
    BaseEvaluatorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.openai.evaluators.openai_evaluator import (
        OpenAIEvaluator,
    )


OPENAI_EVALUATOR_FLAVOR = "openai"


class OpenAIEvaluatorConfig(BaseEvaluatorConfig):
    """Config for the OpenAI-backed evaluator."""

    model: str = Field(
        "gpt-4o-mini",
        description=(
            "OpenAI chat model used as judge. Must support structured "
            "JSON output (response_format). Examples: 'gpt-4o', "
            "'gpt-4o-mini'. Defaults to gpt-4o-mini for cost"
        ),
    )
    temperature: float = Field(
        0.0,
        description=(
            "Sampling temperature for the judge. 0.0 minimizes variance "
            "and is recommended for reproducible eval"
        ),
    )
    max_concurrency: int = Field(
        4,
        description=(
            "Max concurrent requests to OpenAI when evaluating multiple "
            "cases in parallel. Default 4"
        ),
    )
    api_key_secret: Optional[str] = Field(
        None,
        description=(
            "ZenML secret reference holding OPENAI_API_KEY. If unset, "
            "falls back to the OPENAI_API_KEY environment variable"
        ),
    )


class OpenAIEvaluatorFlavor(BaseEvaluatorFlavor):
    """Flavor metadata for OpenAIEvaluator."""

    @property
    def name(self) -> str:
        """The flavor name.

        Returns:
            The string 'openai'.
        """
        return OPENAI_EVALUATOR_FLAVOR

    @property
    def config_class(self) -> Type[OpenAIEvaluatorConfig]:
        """Config class for this flavor.

        Returns:
            OpenAIEvaluatorConfig.
        """
        return OpenAIEvaluatorConfig

    @property
    def implementation_class(self) -> Type["OpenAIEvaluator"]:
        """The evaluator implementation class.

        Returns:
            OpenAIEvaluator, imported lazily to avoid pulling the openai
            package on flavor registration.
        """
        from zenml.integrations.openai.evaluators.openai_evaluator import (
            OpenAIEvaluator,
        )

        return OpenAIEvaluator
