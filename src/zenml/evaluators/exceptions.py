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
"""Exceptions raised by the evaluator framework."""

from typing import Dict

from zenml.evaluators.result import EvaluationMode


class EvaluationModeNotSupportedError(Exception):
    """Raised when a flavor doesn't implement a requested evaluation mode."""

    def __init__(self, flavor: str, mode: EvaluationMode) -> None:
        super().__init__(
            f"Evaluator flavor '{flavor}' does not support mode '{mode}'. "
            f"Switch to a flavor whose `supported_modes` includes "
            f"`EvaluationMode.{mode.name}`."
        )
        self.flavor = flavor
        self.mode = mode


class EvaluationRegressionError(Exception):
    """Raised when an evaluator regressed and on_regression='fail'."""

    def __init__(
        self,
        suite_name: str,
        regressed_metrics: Dict[str, float],
    ) -> None:
        deltas = ", ".join(
            f"{m}: {d:+.3f}" for m, d in regressed_metrics.items()
        )
        super().__init__(
            f"Evaluation suite '{suite_name}' regressed against baseline. "
            f"Deltas: {deltas}"
        )
        self.suite_name = suite_name
        self.regressed_metrics = regressed_metrics
