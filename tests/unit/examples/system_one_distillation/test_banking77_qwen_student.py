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

"""Tests for the Qwen student that reuses stored teacher labels."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from examples.system_one_distillation.banking77_data import (
    Banking77GoldCohort,
    Banking77GoldExample,
    Banking77InputCohort,
    Banking77Question,
    Banking77TeacherInput,
)
from examples.system_one_distillation.banking77_model import TeacherSupervision
from examples.system_one_distillation.banking77_open_teacher import (
    Banking77OpenTeacherLabel,
    OpenTeacherRun,
)
from examples.system_one_distillation.banking77_pipelines import (
    compare_banking77_students,
    distill_banking77_qwen_students,
)
from examples.system_one_distillation.banking77_qwen_student import (
    QwenStudentConfig,
    QwenTrainingStats,
    planned_epochs,
)

from zenml.materializers.materializer_registry import materializer_registry
from zenml.materializers.path_materializer import PathMaterializer

TAXONOMY = {
    "cash_withdrawal": "Cash withdrawal",
    "card_payment": "Card payment",
}
QWEN_MODULE = "examples.system_one_distillation.banking77_qwen_student"


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
    probabilities = {label: 0.1 for label in TAXONOMY}
    probabilities[choice] = 0.9
    return Banking77OpenTeacherLabel(
        example_id=item.example_id,
        chosen_label=choice,
        confidence=0.9,
        probabilities=probabilities,
        input_tokens=10,
        latency_seconds=0.01,
        model_id="fixture/open-jev",
        model_revision="a" * 40,
        code_revision="b" * 40,
    )


@dataclass
class _FakeStudent:
    taxonomy: tuple[str, ...]
    parameter_count: int = 14
    released: bool = False

    def release_gpu_memory(self) -> None:
        self.released = True

    def predict_distributions(
        self, texts: Sequence[str]
    ) -> list[dict[str, float]]:
        return [
            {"cash_withdrawal": 0.8, "card_payment": 0.2}
            if "cash" in text
            else {"cash_withdrawal": 0.2, "card_payment": 0.8}
            for text in texts
        ]


def test_small_rungs_train_for_more_epochs() -> None:
    """Every rung reaches the minimum optimizer-step budget."""
    config = QwenStudentConfig(
        batch_size=16, min_epochs=3, min_optimizer_steps=150
    )

    assert planned_epochs(250, config) == 10
    assert planned_epochs(2_000, config) == 3
    with pytest.raises(ValueError):
        planned_epochs(0, config)


def test_qwen_step_trains_prefixes_on_teacher_labels_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Human labels never reach training, and the largest rung is final.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary directory for the saved student.
    """
    training = (
        _input("train-1", "cash please"),
        _input("train-2", "card charge"),
        _input("train-3", "cash again"),
    )
    teacher_choices = ("card_payment", "card_payment", "cash_withdrawal")
    gold = (
        Banking77GoldExample(
            input=_input("test-1", "cash out"), gold_label="cash_withdrawal"
        ),
    )
    teacher_run = OpenTeacherRun(
        labels=(
            *(
                _teacher_label(item, choice)
                for item, choice in zip(training, teacher_choices)
            ),
            _teacher_label(gold[0].input, "cash_withdrawal"),
        ),
        elapsed_seconds=1.0,
        decisions_per_second=4.0,
        prefix_cache=False,
    )
    seen: list[tuple[tuple[str, str | None], ...]] = []
    students: list[_FakeStudent] = []

    def fake_train(
        examples: Sequence[TeacherSupervision], **kwargs: Any
    ) -> tuple[_FakeStudent, QwenTrainingStats]:
        seen.append(
            tuple((ex.example_id, ex.teacher_label) for ex in examples)
        )
        stats = QwenTrainingStats(
            epochs=3,
            optimizer_steps=3,
            truncated_count=0,
            training_seconds=1.0,
        )
        students.append(_FakeStudent(tuple(kwargs["taxonomy"])))
        return students[-1], stats

    def fake_save(student: _FakeStudent, directory: Path) -> Path:
        tmp_path.joinpath("weights.bin").write_bytes(b"12345")
        return tmp_path

    monkeypatch.setattr(f"{QWEN_MODULE}.train_qwen_student", fake_train)
    monkeypatch.setattr(f"{QWEN_MODULE}.save_qwen_student", fake_save)

    report, output = distill_banking77_qwen_students.entrypoint(
        Banking77InputCohort(items=training),
        Banking77GoldCohort(items=gold),
        teacher_run,
        (2, 3),
        "L40S",
    )

    assert seen == [
        (("train-1", "card_payment"), ("train-2", "card_payment")),
        (
            ("train-1", "card_payment"),
            ("train-2", "card_payment"),
            ("train-3", "cash_withdrawal"),
        ),
    ]
    assert [result.training_size for result in report.rung_results] == [2, 3]
    assert report.final_rung_size == 3
    assert report.rung_results[-1].human_accuracy == 1.0
    assert report.final_model_bytes == 5
    assert report.requested_gpu == "L40S"
    assert report.student_parameter_count == 14
    assert [student.released for student in students] == [True, False]
    assert output == tmp_path


def test_comparison_rejects_reports_from_different_teachers() -> None:
    """Students are only compared when they share a teacher and test set."""
    lexical = type(
        "Report",
        (),
        {"teacher_model_revision": "a" * 40, "test_example_count": 1_000},
    )()
    qwen = type(
        "Report",
        (),
        {"teacher_model_revision": "c" * 40, "test_example_count": 1_000},
    )()

    with pytest.raises(ValueError):
        compare_banking77_students.entrypoint(lexical, qwen)


def test_final_qwen_student_uses_path_materialization() -> None:
    """The saved weight directory is stored as files, not pickled objects."""
    assert materializer_registry[Path] is PathMaterializer
