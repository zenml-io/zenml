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

"""Tests for the pinned Banking77 experiment data contract."""

import json
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from examples.system_one_distillation.banking77_data import (
    BANKING77_CONFIG,
    BANKING77_CRITERIA,
    BANKING77_DATASET_ID,
    BANKING77_INSTRUCTIONS,
    BANKING77_REVISION,
    build_banking77_dataset,
    load_banking77_dataset,
)
from examples.system_one_distillation.contracts import DataContractError


def _row(
    split: str,
    index: int,
    text: str,
    label: str = "activate_my_card",
    *,
    criteria: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    question = {
        "type": "choice",
        "instructions": BANKING77_INSTRUCTIONS,
        "criteria": dict(criteria or BANKING77_CRITERIA),
    }
    return {
        "id": f"banking77/{split}/{index}",
        "source": "banking77",
        "primitive": "choice",
        "split": split,
        "state": json.dumps(text),
        "question": json.dumps(question),
        "label": label,
        "soft_label": None,
    }


def _splits() -> dict[str, list[dict[str, Any]]]:
    return {
        "train": [_row("train", 1, "Please activate my card")],
        "validation": [_row("validation", 2, "Why was my transfer declined?")],
        "test": [_row("test", 3, "My cash withdrawal was declined")],
    }


def test_exact_taxonomy_and_question_are_preserved_without_teacher_labels() -> (
    None
):
    """Teacher inputs remain label-free while evaluation keeps human gold."""
    dataset = build_banking77_dataset(_splits())

    assert len(BANKING77_CRITERIA) == 77
    assert BANKING77_CRITERIA["Refund_not_showing_up"] == (
        "Refund not showing up"
    )
    assert BANKING77_CRITERIA["reverted_card_payment?"] == (
        "Reverted card payment?"
    )
    assert dataset.train_inputs[0].question.instructions == (
        BANKING77_INSTRUCTIONS
    )
    assert dataset.train_inputs[0].question.criteria == BANKING77_CRITERIA
    assert "label" not in dataset.train_inputs[0].model_dump()
    assert "label" not in dataset.development_examples[0].input.model_dump()
    assert dataset.development_examples[0].gold_label == "activate_my_card"
    assert dataset.test_examples[0].gold_label == "activate_my_card"


def test_train_and_development_duplicates_are_removed_without_moving_test() -> (
    None
):
    """Normalized test matches cannot leak into model-development splits."""
    splits = _splits()
    splits["train"].extend(
        [
            _row("train", 4, "  MY CASH withdrawal was\nDECLINED  "),
            _row("train", 5, "A distinct training message"),
        ]
    )
    splits["validation"].append(
        _row(
            "validation",
            6,
            "Ｍｙ cash withdrawal was declined",
            label="declined_cash_withdrawal",
        )
    )
    original_test = list(splits["test"])

    dataset = build_banking77_dataset(splits)

    assert [item.example_id for item in dataset.train_inputs] == [
        "banking77/train/1",
        "banking77/train/5",
    ]
    assert [
        item.input.example_id for item in dataset.development_examples
    ] == ["banking77/validation/2"]
    assert dataset.development_examples[0].gold_label == "activate_my_card"
    assert dataset.removed_duplicate_ids == (
        "banking77/train/4",
        "banking77/validation/6",
    )
    assert [item.input.example_id for item in dataset.test_examples] == [
        original_test[0]["id"]
    ]
    assert dataset.test_examples[0].input.text == json.loads(
        original_test[0]["state"]
    )


def test_lineage_hashes_are_deterministic_and_cover_gold_evaluation() -> None:
    """Every prepared split and held-out label contributes to lineage."""
    first = build_banking77_dataset(_splits())
    second = build_banking77_dataset(_splits())
    changed_splits = _splits()
    changed_splits["test"][0]["label"] = "declined_cash_withdrawal"
    changed = build_banking77_dataset(changed_splits)

    assert first.lineage == second.lineage
    assert first.lineage.dataset_id == BANKING77_DATASET_ID
    assert first.lineage.config == BANKING77_CONFIG
    assert first.lineage.revision == BANKING77_REVISION
    assert first.lineage.dataset_hash.startswith("sha256:")
    assert changed.lineage.train_hash == first.lineage.train_hash
    assert changed.lineage.test_hash != first.lineage.test_hash
    assert changed.lineage.dataset_hash != first.lineage.dataset_hash

    changed_development_splits = _splits()
    changed_development_splits["validation"][0]["label"] = "declined_transfer"
    changed_development = build_banking77_dataset(changed_development_splits)
    assert changed_development.lineage.development_hash != (
        first.lineage.development_hash
    )
    assert changed_development.lineage.test_hash == first.lineage.test_hash


def test_loader_pins_dataset_config_and_revision() -> None:
    """The network boundary cannot silently follow a moving Hub revision."""
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_loader(
        *args: Any, **kwargs: Any
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        calls.append((args, kwargs))
        return _splits()

    dataset = load_banking77_dataset(load_dataset_fn=fake_loader)

    assert dataset.test_examples
    assert calls == [
        (
            (BANKING77_DATASET_ID, BANKING77_CONFIG),
            {"revision": BANKING77_REVISION},
        )
    ]


def test_changed_taxonomy_and_duplicate_ids_are_rejected() -> None:
    """Source drift and ambiguous row identities fail before teacher calls."""
    changed_taxonomy = _splits()
    criteria = dict(BANKING77_CRITERIA)
    criteria["activate_my_card"] = "Activate a card"
    changed_taxonomy["train"][0] = _row(
        "train", 1, "Please activate my card", criteria=criteria
    )
    with pytest.raises(DataContractError, match="changed the pinned question"):
        build_banking77_dataset(changed_taxonomy)

    duplicate_ids = _splits()
    duplicate_ids["test"][0]["id"] = duplicate_ids["train"][0]["id"]
    with pytest.raises(DataContractError, match="duplicate IDs"):
        build_banking77_dataset(duplicate_ids)


def test_validation_split_metadata_is_enforced() -> None:
    """Validation gold cannot be relabeled as another source split."""
    splits = _splits()
    splits["validation"][0]["split"] = "test"

    with pytest.raises(DataContractError, match="invalid split metadata"):
        build_banking77_dataset(splits)


@pytest.mark.parametrize("split", ["validation", "test"])
def test_invalid_evaluation_label_is_rejected(split: str) -> None:
    """Evaluation splits cannot contain labels outside the taxonomy.

    Args:
        split: Validation or test split to corrupt.
    """
    splits = _splits()
    splits[split][0]["label"] = "not_a_real_intent"

    with pytest.raises(DataContractError, match="invalid gold label"):
        build_banking77_dataset(splits)
