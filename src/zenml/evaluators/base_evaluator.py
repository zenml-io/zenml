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
"""Base classes for evaluator stack components."""

from abc import abstractmethod
from typing import List, Set, Type

from zenml.enums import StackComponentType
from zenml.evaluators.cases import (
    PointwiseCase,
    RAGCase,
    ReferenceCase,
    Rubric,
)
from zenml.evaluators.exceptions import EvaluationModeNotSupportedError
from zenml.evaluators.result import EvaluationMode, EvaluationResult
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig


class BaseEvaluatorConfig(StackComponentConfig):
    """Base config for all evaluator flavors.

    Concrete flavors extend this with their own fields (model name,
    API key references, concurrency, etc.).
    """


class BaseEvaluator(StackComponent):
    """Base class for all evaluator stack components.

    A flavor declares which evaluation modes it supports via
    `supported_modes` and overrides the matching `evaluate_*` methods.
    Calling an unsupported mode raises `EvaluationModeNotSupportedError`.
    """

    @property
    @abstractmethod
    def supported_modes(self) -> Set[EvaluationMode]:
        """The evaluation modes this flavor implements."""

    def evaluate_pointwise(
        self,
        cases: List[PointwiseCase],
        rubric: Rubric,
    ) -> EvaluationResult:
        """Score each case against a rubric.

        Args:
            cases: The list of pointwise cases to evaluate.
            rubric: The rubric to score each case against.

        Returns:
            An EvaluationResult containing per-case scores and aggregates.

        Raises:
            EvaluationModeNotSupportedError: Always — override in subclasses
                that declare POINTWISE in supported_modes.
        """
        raise EvaluationModeNotSupportedError(
            self.flavor, EvaluationMode.POINTWISE
        )

    def evaluate_reference(
        self,
        cases: List[ReferenceCase],
        metrics: List[str],
    ) -> EvaluationResult:
        """Score each case against its expected output.

        Args:
            cases: The list of reference cases to evaluate.
            metrics: The metric names to compute.

        Returns:
            An EvaluationResult containing per-case scores and aggregates.

        Raises:
            EvaluationModeNotSupportedError: Always — override in subclasses
                that declare REFERENCE in supported_modes.
        """
        raise EvaluationModeNotSupportedError(
            self.flavor, EvaluationMode.REFERENCE
        )

    def evaluate_rag(
        self,
        cases: List[RAGCase],
        metrics: List[str],
    ) -> EvaluationResult:
        """Score RAG triples (query, context, response).

        Args:
            cases: The list of RAG cases to evaluate.
            metrics: The metric names to compute.

        Returns:
            An EvaluationResult containing per-case scores and aggregates.

        Raises:
            EvaluationModeNotSupportedError: Always — override in subclasses
                that declare RAG in supported_modes.
        """
        raise EvaluationModeNotSupportedError(self.flavor, EvaluationMode.RAG)


class BaseEvaluatorFlavor(Flavor):
    """Base flavor for evaluator stack components.

    Concrete flavors must still implement `name` (required by `Flavor`) and
    override `implementation_class` to return their specific evaluator class.
    """

    @property
    def type(self) -> StackComponentType:
        """Type of the flavor.

        Returns:
            The EVALUATOR stack component type.
        """
        return StackComponentType.EVALUATOR

    @property
    def config_class(self) -> Type[BaseEvaluatorConfig]:
        """Config class for this flavor.

        Returns:
            The base evaluator config class.
        """
        return BaseEvaluatorConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[StackComponent]:
        """Returns the implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        return BaseEvaluator
