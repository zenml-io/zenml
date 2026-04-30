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
"""Unit tests for the OpenAI evaluator flavor."""

from unittest.mock import MagicMock

from zenml.evaluators.cases import PointwiseCase, Rubric
from zenml.evaluators.result import EvaluationMode


def test_supported_modes_includes_all_three():
    from zenml.integrations.openai.evaluators.openai_evaluator import (
        OpenAIEvaluator,
    )
    from zenml.integrations.openai.evaluators.openai_evaluator_flavor import (
        OpenAIEvaluatorConfig,
    )

    config = OpenAIEvaluatorConfig(model="gpt-4o-mini")
    ev = OpenAIEvaluator.__new__(OpenAIEvaluator)
    ev._config = config  # type: ignore[attr-defined]
    assert {
        EvaluationMode.POINTWISE,
        EvaluationMode.REFERENCE,
        EvaluationMode.RAG,
    } <= ev.supported_modes


def test_flavor_metadata():
    from zenml.integrations.openai.evaluators.openai_evaluator import (
        OpenAIEvaluator,
    )
    from zenml.integrations.openai.evaluators.openai_evaluator_flavor import (
        OpenAIEvaluatorConfig,
        OpenAIEvaluatorFlavor,
    )

    f = OpenAIEvaluatorFlavor()
    assert f.name == "openai"
    assert f.config_class is OpenAIEvaluatorConfig
    assert f.implementation_class is OpenAIEvaluator


def test_pointwise_calls_openai_with_rubric(monkeypatch):
    from zenml.integrations.openai.evaluators.openai_evaluator import (
        OpenAIEvaluator,
    )
    from zenml.integrations.openai.evaluators.openai_evaluator_flavor import (
        OpenAIEvaluatorConfig,
    )

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"score": 4}'))]
    )
    monkeypatch.setattr(
        "zenml.integrations.openai.evaluators.openai_evaluator._openai_client",
        lambda cfg: fake_client,
    )
    config = OpenAIEvaluatorConfig(model="gpt-4o-mini")
    ev = OpenAIEvaluator.__new__(OpenAIEvaluator)
    ev._config = config  # type: ignore[attr-defined]

    rubric = Rubric(name="r", criterion="ok?", scale=(1, 5))
    result = ev.evaluate_pointwise(
        [PointwiseCase(input="i", output="o")], rubric
    )
    assert len(result.cases) == 1
    assert result.cases[0].scores["score"] == 4
