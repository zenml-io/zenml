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
"""Ragas-backed evaluator: RAG and reference-based eval."""

from typing import Any, Dict, List, Set

from zenml.evaluators.base_evaluator import BaseEvaluator
from zenml.evaluators.cases import RAGCase, ReferenceCase
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)
from zenml.integrations.ragas.evaluators.ragas_evaluator_flavor import (
    RAGAS_EVALUATOR_FLAVOR,
    RagasEvaluatorConfig,
)


class RagasEvaluator(BaseEvaluator):
    """Evaluator that delegates to the Ragas library.

    Note: Ragas's API surface is young and may shift across versions;
    the exact metric callables in `_run_ragas_*` are pinned via the
    integration's REQUIREMENTS range.
    """

    @property
    def config(self) -> RagasEvaluatorConfig:
        """Return the evaluator's typed config.

        Returns:
            The RagasEvaluatorConfig for this instance.
        """
        return self._config  # type: ignore[return-value]

    @property
    def supported_modes(self) -> Set[EvaluationMode]:
        """The evaluation modes this flavor implements.

        Ragas is purpose-built for RAG pipelines and reference-based
        comparison; pointwise rubric scoring is not in scope.

        Returns:
            RAG and REFERENCE evaluation modes.
        """
        return {EvaluationMode.RAG, EvaluationMode.REFERENCE}

    def evaluate_rag(
        self,
        cases: List[RAGCase],
        metrics: List[str],
    ) -> EvaluationResult:
        """Score RAG triples using Ragas metrics.

        Args:
            cases: The list of RAG cases to evaluate.
            metrics: Ragas metric names to compute (e.g., 'faithfulness').

        Returns:
            An EvaluationResult with per-case metric scores.
        """
        ragas_results = self._run_ragas_rag(cases, metrics)
        cases_out = [
            CaseResult(
                case_id=str(i),
                scores=ragas_results[i],
                passed=True,
                raw={},
            )
            for i in range(len(cases))
        ]
        return EvaluationResult(
            evaluator=RAGAS_EVALUATOR_FLAVOR,
            mode=EvaluationMode.RAG,
            suite_name="",
            cases=cases_out,
            aggregates={},
            metadata={
                "judge_model": self.config.judge_model,
                "metrics": metrics,
            },
        )

    def evaluate_reference(
        self,
        cases: List[ReferenceCase],
        metrics: List[str],
    ) -> EvaluationResult:
        """Score cases against reference outputs using Ragas metrics.

        Args:
            cases: The list of reference cases to evaluate.
            metrics: Ragas metric names to compute (e.g.,
                'answer_correctness').

        Returns:
            An EvaluationResult with per-case metric scores.
        """
        ragas_results = self._run_ragas_reference(cases, metrics)
        cases_out = [
            CaseResult(
                case_id=str(i),
                scores=ragas_results[i],
                passed=True,
                raw={},
            )
            for i in range(len(cases))
        ]
        return EvaluationResult(
            evaluator=RAGAS_EVALUATOR_FLAVOR,
            mode=EvaluationMode.REFERENCE,
            suite_name="",
            cases=cases_out,
            aggregates={},
            metadata={
                "judge_model": self.config.judge_model,
                "metrics": metrics,
            },
        )

    def _run_ragas_rag(
        self,
        cases: List[RAGCase],
        metrics: List[str],
    ) -> List[Dict[str, float]]:
        # TODO: verify against pinned ragas (>=0.2,<0.4). The exact
        # result-unwrapping shape and metric callable names may change
        # between Ragas releases; the pseudocode below targets the 0.2.x
        # API where `evaluate()` returns a `Result` object indexable by
        # row and `metric.name` gives the string key.
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        metric_map: Dict[str, Any] = {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
            "context_recall": context_recall,
        }
        chosen = [metric_map[m] for m in metrics if m in metric_map]
        ds = Dataset.from_dict(
            {
                "question": [c.query for c in cases],
                "contexts": [c.context for c in cases],
                "answer": [c.response for c in cases],
                "ground_truth": [c.expected_answer or "" for c in cases],
            }
        )
        result = evaluate(ds, metrics=chosen)
        return [
            {m.name: float(result[i][m.name]) for m in chosen}
            for i in range(len(cases))
        ]

    def _run_ragas_reference(
        self,
        cases: List[ReferenceCase],
        metrics: List[str],
    ) -> List[Dict[str, float]]:
        # TODO: verify against pinned ragas (>=0.2,<0.4). Same caveats
        # apply as in _run_ragas_rag regarding API stability.
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_correctness, answer_similarity

        metric_map: Dict[str, Any] = {
            "answer_correctness": answer_correctness,
            "answer_similarity": answer_similarity,
        }
        chosen = [metric_map[m] for m in metrics if m in metric_map]
        ds = Dataset.from_dict(
            {
                "question": [c.input for c in cases],
                "answer": [c.output for c in cases],
                "ground_truth": [c.expected for c in cases],
            }
        )
        result = evaluate(ds, metrics=chosen)
        return [
            {m.name: float(result[i][m.name]) for m in chosen}
            for i in range(len(cases))
        ]
