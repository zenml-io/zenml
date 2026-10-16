#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

"""Tests for the multiclass lexical Jev replacement."""

import json
from pathlib import Path

import pytest
from examples.system_one_distillation.banking77_model import (
    TeacherSupervision,
    evaluate_student,
    load_lexical_student,
    save_lexical_student,
    train_lexical_student,
    train_nested_rungs,
)

TAXONOMY = ("cash_withdrawal", "card_payment", "bank_transfer")


def _examples() -> list[TeacherSupervision]:
    return [
        TeacherSupervision(
            "cash-1", "cash machine did not give my money", "cash_withdrawal"
        ),
        TeacherSupervision(
            "card-1", "card purchase appears twice", "card_payment"
        ),
        TeacherSupervision(
            "transfer-1",
            "bank transfer recipient has not received it",
            "bank_transfer",
        ),
        TeacherSupervision(
            "cash-soft",
            "cash withdrawal fee at an ATM",
            teacher_distribution={
                "cash_withdrawal": 0.90,
                "card_payment": 0.05,
                "bank_transfer": 0.05,
            },
        ),
        TeacherSupervision(
            "card-2", "cash card payment was declined", "card_payment"
        ),
        TeacherSupervision(
            "transfer-2", "cancel my pending transfer", "bank_transfer"
        ),
    ]


def test_trains_from_hard_and_soft_teacher_targets() -> None:
    """Soft distributions and hard labels share one teacher-only contract."""
    student = train_lexical_student(
        _examples(), taxonomy=TAXONOMY, epochs=80, learning_rate=1.0
    )

    distributions = student.predict_distributions(
        ["ATM cash withdrawal", "recipient missing bank transfer"]
    )

    assert set(distributions[0]) == set(TAXONOMY)
    assert sum(distributions[0].values()) == pytest.approx(1.0)
    assert (
        max(distributions[0], key=distributions[0].__getitem__)
        == "cash_withdrawal"
    )
    assert (
        max(distributions[1], key=distributions[1].__getitem__)
        == "bank_transfer"
    )
    assert student.predict_distributions([]) == []


def test_nested_rungs_record_strict_training_prefixes() -> None:
    """Every larger learning-curve rung contains the exact smaller prefix."""
    examples = _examples()
    rungs = train_nested_rungs(
        examples,
        taxonomy=TAXONOMY,
        rung_sizes=(3, 5, 6),
        epochs=2,
    )

    assert tuple(rungs) == (3, 5, 6)
    assert rungs[3].training_example_ids == tuple(
        example.example_id for example in examples[:3]
    )
    assert rungs[5].training_example_ids[:3] == rungs[3].training_example_ids
    assert rungs[6].training_example_ids[:5] == rungs[5].training_example_ids


def test_safe_json_round_trip_preserves_full_distributions(
    tmp_path: Path,
) -> None:
    """The JSON artifact reloads identically without executable pickle data.

    Args:
        tmp_path: Pytest-managed temporary directory.
    """
    student = train_lexical_student(_examples(), taxonomy=TAXONOMY, epochs=5)
    path = tmp_path / "student.json"
    before = student.predict_distributions(["cash machine withdrawal"])

    save_lexical_student(path, student)
    loaded = load_lexical_student(path)

    assert loaded.predict_distributions(
        ["cash machine withdrawal"]
    ) == pytest.approx(before)
    assert (
        json.loads(path.read_text())["model_type"] == "word-char-tfidf-softmax"
    )


def test_loader_rejects_inconsistent_model_width(tmp_path: Path) -> None:
    """Untrusted JSON cannot silently alter the linear-head dimensions.

    Args:
        tmp_path: Pytest-managed temporary directory.
    """
    student = train_lexical_student(_examples(), taxonomy=TAXONOMY, epochs=2)
    path = tmp_path / "student.json"
    save_lexical_student(path, student)
    payload = json.loads(path.read_text())
    payload["coefficients"][0].pop()
    path.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="invalid"):
        load_lexical_student(path)


def test_evaluation_separates_human_quality_from_teacher_agreement() -> None:
    """Perfect teacher imitation can still disagree with human ground truth."""
    student = train_lexical_student(
        _examples(), taxonomy=TAXONOMY, epochs=80, learning_rate=1.0
    )
    texts = ["cash machine kept my card cash", "recipient missing transfer"]
    predictions = student.predict(texts)
    human_labels = (
        "card_payment"
        if predictions[0] == "cash_withdrawal"
        else "cash_withdrawal",
        "card_payment"
        if predictions[1] == "bank_transfer"
        else "bank_transfer",
    )

    metrics = evaluate_student(
        student,
        texts=texts,
        human_labels=human_labels,
        teacher_labels=predictions,
        ece_bins=5,
    )

    assert metrics.evaluated_count == 2
    assert metrics.accuracy == 0.0
    assert metrics.macro_f1 == 0.0
    assert metrics.teacher_agreement == 1.0
    assert metrics.negative_log_likelihood > 0.0
    assert 0.0 <= metrics.brier_score <= 2.0
    assert 0.0 <= metrics.top_label_ece <= 1.0


@pytest.mark.parametrize(
    "example",
    [
        TeacherSupervision("missing", "some text"),
        TeacherSupervision(
            "both",
            "some text",
            teacher_label="card_payment",
            teacher_distribution={"card_payment": 1.0},
        ),
        TeacherSupervision(
            "unknown",
            "some text",
            teacher_distribution={"not_in_taxonomy": 1.0},
        ),
    ],
)
def test_invalid_teacher_targets_are_rejected(
    example: TeacherSupervision,
) -> None:
    """Malformed teacher supervision cannot enter a training rung.

    Args:
        example: Invalid teacher target supplied by parametrization.
    """
    with pytest.raises(ValueError):
        train_lexical_student([example], taxonomy=TAXONOMY, epochs=1)
