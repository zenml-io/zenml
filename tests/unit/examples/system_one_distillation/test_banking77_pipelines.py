#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Tests for the complete Banking77 distillation pipeline."""

from typing import Any, get_args, get_type_hints

import pytest
from examples.system_one_distillation.banking77_data import (
    Banking77GoldCohort,
    Banking77GoldExample,
    Banking77InputCohort,
    Banking77Lineage,
    Banking77Question,
    Banking77TeacherInput,
)
from examples.system_one_distillation.banking77_model import (
    LexicalMulticlassStudent,
)
from examples.system_one_distillation.banking77_open_teacher import (
    Banking77OpenTeacherLabel,
    OpenTeacherRun,
)
from examples.system_one_distillation.banking77_pipelines import (
    distill_banking77_students,
    label_complete_banking77_cohort,
    merge_open_teacher_shards,
    shard_complete_banking77_cohort,
)

from zenml.materializers import DataclassMaterializer
from zenml.materializers.materializer_registry import materializer_registry

TAXONOMY = {
    "cash_withdrawal": "Cash withdrawal",
    "card_payment": "Card payment",
    "bank_transfer": "Bank transfer",
}


def _input(example_id: str, text: str) -> Banking77TeacherInput:
    return Banking77TeacherInput(
        example_id=example_id,
        text=text,
        question=Banking77Question(
            instructions="Choose the banking intent.", criteria=TAXONOMY
        ),
    )


def _teacher_label(
    item: Banking77TeacherInput, choice: str
) -> Banking77OpenTeacherLabel:
    probabilities = {label: 0.05 for label in TAXONOMY}
    probabilities[choice] = 0.90
    return Banking77OpenTeacherLabel(
        example_id=item.example_id,
        chosen_label=choice,
        confidence=0.90,
        probabilities=probabilities,
        input_tokens=10,
        latency_seconds=0.01,
        model_id="fixture/open-jev",
        model_revision="a" * 40,
        code_revision="b" * 40,
    )


def _lineage() -> Banking77Lineage:
    digest = "sha256:" + "0" * 64
    return Banking77Lineage(
        question_hash=digest,
        train_hash=digest,
        development_hash=digest,
        test_hash=digest,
        removed_duplicates_hash=digest,
        dataset_hash=digest,
    )


def test_complete_label_step_calls_teacher_once_with_train_then_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The GPU boundary receives one combined, label-free cohort.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    training = (_input("train-1", "cash from ATM"),)
    test = (_input("test-1", "card purchase"),)
    calls: list[tuple[str, ...]] = []

    def fake_label(inputs: Any, **kwargs: Any) -> OpenTeacherRun:
        calls.append(tuple(item.example_id for item in inputs))
        return OpenTeacherRun(
            labels=tuple(),
            elapsed_seconds=0.0,
            decisions_per_second=0.0,
            prefix_cache=False,
        )

    monkeypatch.setattr(
        "examples.system_one_distillation.banking77_pipelines.label_with_open_teacher",
        fake_label,
    )

    label_complete_banking77_cohort.entrypoint(
        Banking77InputCohort(items=training),
        Banking77InputCohort(items=test),
    )

    assert calls == [("train-1", "test-1")]


def test_distillation_reports_all_rungs_and_uses_largest_model() -> None:
    """Test metrics cannot select a smaller final model."""
    training = (
        _input("cash-1", "cash machine withdrawal"),
        _input("card-1", "card purchase charged"),
        _input("transfer-1", "bank transfer recipient"),
        _input("cash-2", "ATM cash fee"),
        _input("card-2", "card payment reversed"),
        _input("transfer-2", "cancel bank transfer"),
    )
    gold = (
        Banking77GoldExample(
            input=_input("test-cash", "cash withdrawal at ATM"),
            gold_label="cash_withdrawal",
        ),
        Banking77GoldExample(
            input=_input("test-transfer", "recipient did not get transfer"),
            gold_label="bank_transfer",
        ),
    )
    choices = (
        "cash_withdrawal",
        "card_payment",
        "bank_transfer",
        "cash_withdrawal",
        "card_payment",
        "bank_transfer",
        "cash_withdrawal",
        "bank_transfer",
    )
    all_inputs = (*training, *(example.input for example in gold))
    teacher_run = OpenTeacherRun(
        labels=tuple(
            _teacher_label(item, choice)
            for item, choice in zip(all_inputs, choices)
        ),
        elapsed_seconds=4.0,
        decisions_per_second=2.0,
        prefix_cache=False,
    )

    report, final_student = distill_banking77_students.entrypoint(
        Banking77InputCohort(items=training),
        Banking77GoldCohort(items=gold),
        teacher_run,
        _lineage(),
        tuple(),
        (3, 6),
    )

    assert [result.training_size for result in report.rung_results] == [3, 6]
    assert report.final_rung_size == 6
    assert report.teacher_human_metrics.accuracy == 1.0
    assert report.teacher_decision_count == 8
    assert report.teacher_inference_decisions_per_second == 2.0
    assert report.teacher_worker_count == 1
    assert report.teacher_worker_inference_seconds == (4.0,)
    assert report.teacher_total_worker_inference_seconds == 4.0
    assert report.teacher_batch_size == 32
    assert report.teacher_prefix_cache is False
    assert report.teacher_requested_gpu == "unspecified"
    assert report.teacher_model_revision == "a" * 40
    assert final_student.training_example_ids == tuple(
        item.example_id for item in training
    )


def test_teacher_partition_rejects_unexpected_labels() -> None:
    """Train and test are separated by identity rather than output order."""
    training = (_input("train", "cash"),)
    gold = (
        Banking77GoldExample(
            input=_input("test", "card"), gold_label="card_payment"
        ),
    )
    teacher_run = OpenTeacherRun(
        labels=(
            _teacher_label(training[0], "cash_withdrawal"),
            _teacher_label(_input("unexpected", "other"), "card_payment"),
        ),
        elapsed_seconds=1.0,
        decisions_per_second=2.0,
        prefix_cache=False,
    )

    with pytest.raises(ValueError, match="exactly cover"):
        distill_banking77_students.entrypoint(
            Banking77InputCohort(items=training),
            Banking77GoldCohort(items=gold),
            teacher_run,
            _lineage(),
            tuple(),
            (1,),
        )


def test_complete_label_step_rejects_overlapping_ids() -> None:
    """One identity cannot belong to train and held-out data."""
    training = (_input("same", "cash"),)
    test = (_input("same", "card"),)

    with pytest.raises(ValueError, match="overlap"):
        label_complete_banking77_cohort.entrypoint(
            Banking77InputCohort(items=training),
            Banking77InputCohort(items=test),
        )


def test_complete_cohort_is_split_into_balanced_ordered_shards() -> None:
    """Parallel workers preserve one deterministic combined input order."""
    training = tuple(
        _input(f"train-{index}", f"training text {index}")
        for index in range(5)
    )
    test = tuple(
        _input(f"test-{index}", f"test text {index}") for index in range(4)
    )

    shards = shard_complete_banking77_cohort.entrypoint(
        Banking77InputCohort(items=training),
        Banking77InputCohort(items=test),
    )

    assert [len(shard.items) for shard in shards] == [3, 2, 2, 2]
    assert [item.example_id for shard in shards for item in shard.items] == [
        item.example_id for item in (*training, *test)
    ]


def test_teacher_shards_merge_with_parallel_runtime_evidence() -> None:
    """Merged throughput uses wall time while retaining total GPU time."""
    inputs = tuple(
        _input(f"item-{index}", f"text {index}") for index in range(4)
    )
    shards = tuple(
        OpenTeacherRun(
            labels=(_teacher_label(item, "cash_withdrawal"),),
            elapsed_seconds=float(index),
            decisions_per_second=1.0 / index,
            prefix_cache=False,
            worker_elapsed_seconds=(float(index),),
        )
        for index, item in enumerate(inputs, start=1)
    )

    merged = merge_open_teacher_shards.entrypoint(*shards)

    assert [label.example_id for label in merged.labels] == [
        item.example_id for item in inputs
    ]
    assert merged.elapsed_seconds == 4.0
    assert merged.decisions_per_second == 1.0
    assert merged.worker_elapsed_seconds == (1.0, 2.0, 3.0, 4.0)


def test_final_student_uses_json_dataclass_materialization() -> None:
    """The public model artifact must not fall back to Cloudpickle."""
    return_type = get_type_hints(
        distill_banking77_students.entrypoint, include_extras=True
    )["return"]
    model_annotation = get_args(return_type)[1]
    model_type = get_args(model_annotation)[0]

    assert model_type is LexicalMulticlassStudent
    assert materializer_registry[model_type] is DataclassMaterializer
