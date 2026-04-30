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
"""OpenAI-backed evaluator: LLM-as-judge across all three v1 modes."""

import json
from typing import Any, Dict, List, Set, Tuple

from zenml.evaluators.base_evaluator import BaseEvaluator
from zenml.evaluators.cases import (
    PointwiseCase,
    RAGCase,
    ReferenceCase,
    Rubric,
)
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)
from zenml.integrations.openai.evaluators.openai_evaluator_flavor import (
    OPENAI_EVALUATOR_FLAVOR,
    OpenAIEvaluatorConfig,
)


def _openai_client(config: OpenAIEvaluatorConfig) -> Any:
    """Return a configured OpenAI client.

    Imported lazily to avoid pulling the openai dependency on flavor-
    registration. Resolves the API key from a ZenML secret if
    `api_key_secret` is set, else from the OPENAI_API_KEY env var.

    Args:
        config: The evaluator config holding model and auth settings.

    Returns:
        An openai.OpenAI client instance.
    """
    from openai import OpenAI

    if config.api_key_secret:
        from zenml.client import Client as ZenClient

        secret = ZenClient().get_secret(config.api_key_secret)
        api_key = secret.values["OPENAI_API_KEY"]
        return OpenAI(api_key=api_key)
    return OpenAI()


class OpenAIEvaluator(BaseEvaluator):
    """LLM-as-judge evaluator backed by an OpenAI chat model."""

    @property
    def config(self) -> OpenAIEvaluatorConfig:
        """Return the evaluator's typed config.

        Returns:
            The OpenAIEvaluatorConfig for this instance.
        """
        return self._config  # type: ignore[return-value]

    @property
    def supported_modes(self) -> Set[EvaluationMode]:
        """The evaluation modes this flavor implements.

        Returns:
            All three v1 evaluation modes.
        """
        return {
            EvaluationMode.POINTWISE,
            EvaluationMode.REFERENCE,
            EvaluationMode.RAG,
        }

    def evaluate_pointwise(
        self,
        cases: List[PointwiseCase],
        rubric: Rubric,
    ) -> EvaluationResult:
        """Score each case against a rubric using an OpenAI judge.

        Args:
            cases: The list of pointwise cases to evaluate.
            rubric: The rubric to score each case against.

        Returns:
            An EvaluationResult with per-case scores from the LLM judge.
        """
        client = _openai_client(self.config)
        cases_out: List[CaseResult] = []
        for i, case in enumerate(cases):
            score, raw = self._judge_pointwise(client, case, rubric)
            cases_out.append(
                CaseResult(
                    case_id=str(i),
                    scores={"score": float(score)},
                    passed=True,  # threshold applied later in the step
                    raw=raw,
                )
            )
        return EvaluationResult(
            evaluator=OPENAI_EVALUATOR_FLAVOR,
            mode=EvaluationMode.POINTWISE,
            suite_name="",  # set by the step wrapper
            cases=cases_out,
            aggregates={},  # recomputed in the step wrapper
            metadata={"model": self.config.model},
        )

    def _judge_pointwise(
        self,
        client: Any,
        case: PointwiseCase,
        rubric: Rubric,
    ) -> Tuple[int, Dict[str, Any]]:
        """Call the OpenAI judge for a single pointwise case.

        Args:
            client: A configured OpenAI client.
            case: The case to evaluate.
            rubric: The rubric defining the scoring criterion and scale.

        Returns:
            A tuple of (integer score, raw parsed JSON dict).
        """
        lo, hi = rubric.scale
        prompt = (
            f"You are evaluating the following output against this rubric.\n"
            f"Rubric: {rubric.criterion}\n"
            f"Score on a scale from {lo} to {hi}.\n"
            f"Input: {case.input}\nOutput: {case.output}\n"
            f'Reply with strict JSON: {{"score": <int>}}'
        )
        resp = client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = json.loads(resp.choices[0].message.content)
        return parsed["score"], parsed

    def evaluate_reference(
        self,
        cases: List[ReferenceCase],
        metrics: List[str],
    ) -> EvaluationResult:
        """Score each case against its expected output using an OpenAI judge.

        Args:
            cases: The list of reference cases to evaluate.
            metrics: The metric names to compute.

        Returns:
            An EvaluationResult with semantic equivalence scores.
        """
        client = _openai_client(self.config)
        cases_out: List[CaseResult] = []
        for i, case in enumerate(cases):
            equiv, raw = self._judge_reference(client, case)
            cases_out.append(
                CaseResult(
                    case_id=str(i),
                    scores={"equivalence": 1.0 if equiv else 0.0},
                    passed=True,
                    raw=raw,
                )
            )
        return EvaluationResult(
            evaluator=OPENAI_EVALUATOR_FLAVOR,
            mode=EvaluationMode.REFERENCE,
            suite_name="",
            cases=cases_out,
            aggregates={},
            metadata={"model": self.config.model, "metrics": metrics},
        )

    def _judge_reference(
        self,
        client: Any,
        case: ReferenceCase,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Call the OpenAI judge to determine semantic equivalence.

        Args:
            client: A configured OpenAI client.
            case: The reference case with expected and actual outputs.

        Returns:
            A tuple of (is_equivalent bool, raw parsed JSON dict).
        """
        prompt = (
            f"Are these two outputs semantically equivalent?\n"
            f"Expected: {case.expected}\nActual: {case.output}\n"
            f'Reply with strict JSON: {{"equivalent": <true|false>}}'
        )
        resp = client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = json.loads(resp.choices[0].message.content)
        return bool(parsed["equivalent"]), parsed

    def evaluate_rag(
        self,
        cases: List[RAGCase],
        metrics: List[str],
    ) -> EvaluationResult:
        """Score RAG triples (query, context, response) using an OpenAI judge.

        Args:
            cases: The list of RAG cases to evaluate.
            metrics: The metric names to compute (e.g., 'faithfulness').

        Returns:
            An EvaluationResult with per-metric float scores per case.
        """
        client = _openai_client(self.config)
        cases_out: List[CaseResult] = []
        for i, case in enumerate(cases):
            scores, raw = self._judge_rag(client, case, metrics)
            cases_out.append(
                CaseResult(
                    case_id=str(i),
                    scores=scores,
                    passed=True,
                    raw=raw,
                )
            )
        return EvaluationResult(
            evaluator=OPENAI_EVALUATOR_FLAVOR,
            mode=EvaluationMode.RAG,
            suite_name="",
            cases=cases_out,
            aggregates={},
            metadata={"model": self.config.model, "metrics": metrics},
        )

    def _judge_rag(
        self,
        client: Any,
        case: RAGCase,
        metrics: List[str],
    ) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """Call the OpenAI judge to score a RAG triple across multiple metrics.

        Args:
            client: A configured OpenAI client.
            case: The RAG case with query, context, and response.
            metrics: Metric names to score in [0.0, 1.0].

        Returns:
            A tuple of ({metric: score} dict, raw parsed JSON dict).
        """
        prompt = (
            "You are evaluating a retrieval-augmented response. "
            "Score each metric in [0.0, 1.0]:\n"
            f"Metrics: {metrics}\n"
            f"Query: {case.query}\n"
            f"Context: {case.context}\nResponse: {case.response}\n"
            'Reply with strict JSON: {"<metric>": <float>, ...}'
        )
        resp = client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = json.loads(resp.choices[0].message.content)
        scores = {m: float(parsed[m]) for m in metrics if m in parsed}
        return scores, parsed
