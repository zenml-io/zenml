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
"""Config and Flavor for RagasEvaluator."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.evaluators.base_evaluator import (
    BaseEvaluatorConfig,
    BaseEvaluatorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.ragas.evaluators.ragas_evaluator import (
        RagasEvaluator,
    )


RAGAS_EVALUATOR_FLAVOR = "ragas"


class RagasEvaluatorConfig(BaseEvaluatorConfig):
    """Config for the Ragas-backed evaluator."""

    judge_model_provider: str = Field(
        "openai",
        description=(
            "LLM provider Ragas uses as judge. Examples: 'openai', "
            "'anthropic'. Defaults to openai"
        ),
    )
    judge_model: str = Field(
        "gpt-4o-mini",
        description=(
            "Specific judge model identifier within the provider. "
            "Example: 'gpt-4o-mini' for openai. Defaults to gpt-4o-mini"
        ),
    )
    embedding_model: Optional[str] = Field(
        None,
        description=(
            "Embedding model used for Ragas similarity metrics. "
            "Example: 'text-embedding-3-small'. Defaults to Ragas's "
            "built-in default for the provider"
        ),
    )


class RagasEvaluatorFlavor(BaseEvaluatorFlavor):
    """Flavor metadata for RagasEvaluator."""

    @property
    def name(self) -> str:
        """The flavor name.

        Returns:
            The string 'ragas'.
        """
        return RAGAS_EVALUATOR_FLAVOR

    @property
    def config_class(self) -> Type[RagasEvaluatorConfig]:
        """Config class for this flavor.

        Returns:
            RagasEvaluatorConfig.
        """
        return RagasEvaluatorConfig

    @property
    def implementation_class(self) -> Type["RagasEvaluator"]:
        """The evaluator implementation class.

        Returns:
            RagasEvaluator, imported lazily to avoid pulling the ragas
            package on flavor registration.
        """
        from zenml.integrations.ragas.evaluators.ragas_evaluator import (
            RagasEvaluator,
        )

        return RagasEvaluator
