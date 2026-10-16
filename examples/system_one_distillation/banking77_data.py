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

"""Pinned Banking77 inputs and held-out evaluation contracts."""

import hashlib
import json
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final, Literal

from examples.system_one_distillation.contracts import (
    ContractModel,
    DataContractError,
)
from pydantic import Field

BANKING77_DATASET_ID: Final = "Praveenrajus/jev-bench"
BANKING77_CONFIG: Final = "banking77"
BANKING77_REVISION: Final = "59d35a0ea406d75c55b3030cd52d9177abfde466"
BANKING77_INSTRUCTIONS = (
    "Which banking support intent does the customer's message express?"
)

# These keys and descriptions intentionally retain the source's capitalization
# and punctuation. They are part of the model-visible contract at the pinned
# dataset revision, rather than a cleaned version of the upstream taxonomy.
BANKING77_CRITERIA: dict[str, str] = {
    "Refund_not_showing_up": "Refund not showing up",
    "activate_my_card": "Activate my card",
    "age_limit": "Age limit",
    "apple_pay_or_google_pay": "Apple pay or google pay",
    "atm_support": "Atm support",
    "automatic_top_up": "Automatic top up",
    "balance_not_updated_after_bank_transfer": (
        "Balance not updated after bank transfer"
    ),
    "balance_not_updated_after_cheque_or_cash_deposit": (
        "Balance not updated after cheque or cash deposit"
    ),
    "beneficiary_not_allowed": "Beneficiary not allowed",
    "cancel_transfer": "Cancel transfer",
    "card_about_to_expire": "Card about to expire",
    "card_acceptance": "Card acceptance",
    "card_arrival": "Card arrival",
    "card_delivery_estimate": "Card delivery estimate",
    "card_linking": "Card linking",
    "card_not_working": "Card not working",
    "card_payment_fee_charged": "Card payment fee charged",
    "card_payment_not_recognised": "Card payment not recognised",
    "card_payment_wrong_exchange_rate": "Card payment wrong exchange rate",
    "card_swallowed": "Card swallowed",
    "cash_withdrawal_charge": "Cash withdrawal charge",
    "cash_withdrawal_not_recognised": "Cash withdrawal not recognised",
    "change_pin": "Change pin",
    "compromised_card": "Compromised card",
    "contactless_not_working": "Contactless not working",
    "country_support": "Country support",
    "declined_card_payment": "Declined card payment",
    "declined_cash_withdrawal": "Declined cash withdrawal",
    "declined_transfer": "Declined transfer",
    "direct_debit_payment_not_recognised": (
        "Direct debit payment not recognised"
    ),
    "disposable_card_limits": "Disposable card limits",
    "edit_personal_details": "Edit personal details",
    "exchange_charge": "Exchange charge",
    "exchange_rate": "Exchange rate",
    "exchange_via_app": "Exchange via app",
    "extra_charge_on_statement": "Extra charge on statement",
    "failed_transfer": "Failed transfer",
    "fiat_currency_support": "Fiat currency support",
    "get_disposable_virtual_card": "Get disposable virtual card",
    "get_physical_card": "Get physical card",
    "getting_spare_card": "Getting spare card",
    "getting_virtual_card": "Getting virtual card",
    "lost_or_stolen_card": "Lost or stolen card",
    "lost_or_stolen_phone": "Lost or stolen phone",
    "order_physical_card": "Order physical card",
    "passcode_forgotten": "Passcode forgotten",
    "pending_card_payment": "Pending card payment",
    "pending_cash_withdrawal": "Pending cash withdrawal",
    "pending_top_up": "Pending top up",
    "pending_transfer": "Pending transfer",
    "pin_blocked": "Pin blocked",
    "receiving_money": "Receiving money",
    "request_refund": "Request refund",
    "reverted_card_payment?": "Reverted card payment?",
    "supported_cards_and_currencies": "Supported cards and currencies",
    "terminate_account": "Terminate account",
    "top_up_by_bank_transfer_charge": "Top up by bank transfer charge",
    "top_up_by_card_charge": "Top up by card charge",
    "top_up_by_cash_or_cheque": "Top up by cash or cheque",
    "top_up_failed": "Top up failed",
    "top_up_limits": "Top up limits",
    "top_up_reverted": "Top up reverted",
    "topping_up_by_card": "Topping up by card",
    "transaction_charged_twice": "Transaction charged twice",
    "transfer_fee_charged": "Transfer fee charged",
    "transfer_into_account": "Transfer into account",
    "transfer_not_received_by_recipient": (
        "Transfer not received by recipient"
    ),
    "transfer_timing": "Transfer timing",
    "unable_to_verify_identity": "Unable to verify identity",
    "verify_my_identity": "Verify my identity",
    "verify_source_of_funds": "Verify source of funds",
    "verify_top_up": "Verify top up",
    "virtual_card_not_working": "Virtual card not working",
    "visa_or_mastercard": "Visa or mastercard",
    "why_verify_identity": "Why verify identity",
    "wrong_amount_of_cash_received": "Wrong amount of cash received",
    "wrong_exchange_rate_for_cash_withdrawal": (
        "Wrong exchange rate for cash withdrawal"
    ),
}


class Banking77Question(ContractModel):
    """The exact choice question shipped with the pinned dataset revision."""

    type: Literal["choice"] = "choice"
    instructions: str = Field(min_length=1)
    criteria: dict[str, str]


class Banking77TeacherInput(ContractModel):
    """A label-free message that may be sent to the teacher."""

    example_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    question: Banking77Question


class Banking77GoldExample(ContractModel):
    """An isolated held-out input and its human evaluation label."""

    input: Banking77TeacherInput
    gold_label: str = Field(min_length=1)


class Banking77InputCohort(ContractModel):
    """One materializable collection of label-free teacher inputs."""

    items: tuple[Banking77TeacherInput, ...]


class Banking77GoldCohort(ContractModel):
    """One materializable collection of held-out human examples."""

    items: tuple[Banking77GoldExample, ...]


class Banking77Lineage(ContractModel):
    """Hashes binding the prepared experiment to its exact source records."""

    dataset_id: Literal["Praveenrajus/jev-bench"] = BANKING77_DATASET_ID
    config: Literal["banking77"] = BANKING77_CONFIG
    revision: Literal["59d35a0ea406d75c55b3030cd52d9177abfde466"] = (
        BANKING77_REVISION
    )
    question_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    train_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    development_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    test_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    removed_duplicates_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    dataset_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class Banking77Dataset(ContractModel):
    """Leakage-resistant splits prepared for teacher/student evaluation."""

    train_inputs: tuple[Banking77TeacherInput, ...]
    development_examples: tuple[Banking77GoldExample, ...]
    test_examples: tuple[Banking77GoldExample, ...]
    removed_duplicate_ids: tuple[str, ...]
    lineage: Banking77Lineage


DatasetLoader = Callable[..., Mapping[str, Sequence[Mapping[str, Any]]]]


def load_banking77_dataset(
    *, load_dataset_fn: DatasetLoader | None = None
) -> Banking77Dataset:
    """Download and prepare the pinned jev-bench Banking77 configuration.

    Args:
        load_dataset_fn: Optional injectable Hugging Face loader for tests.

    Returns:
        Label-free train inputs and isolated development/test gold examples.

    Raises:
        RuntimeError: If the optional ``datasets`` package is unavailable.
    """
    if load_dataset_fn is None:
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional 'datasets' package to load Banking77."
            ) from exc
        load_dataset_fn = load_dataset

    raw_splits = load_dataset_fn(
        BANKING77_DATASET_ID,
        BANKING77_CONFIG,
        revision=BANKING77_REVISION,
    )
    return build_banking77_dataset(raw_splits)


def build_banking77_dataset(
    raw_splits: Mapping[str, Sequence[Mapping[str, Any]]],
) -> Banking77Dataset:
    """Validate source rows, isolate gold labels, and remove test duplicates.

    Text normalization is used only for leakage detection. Test rows remain in
    their original order and unchanged; matching train inputs or complete
    development examples are removed instead.

    Args:
        raw_splits: Mapping containing ``train``, ``validation``, and ``test``.

    Returns:
        A validated dataset with deterministic lineage hashes.

    Raises:
        DataContractError: If splits, identities, questions, or labels are
            invalid.
    """
    missing = {"train", "validation", "test"}.difference(raw_splits)
    if missing:
        raise DataContractError(
            f"Banking77 source is missing splits: {sorted(missing)!r}"
        )

    question = _expected_question()
    train = _parse_inputs(raw_splits["train"], "train", question)
    development = _parse_gold_examples(
        raw_splits["validation"], "validation", question
    )
    test = _parse_gold_examples(raw_splits["test"], "test", question)
    _validate_unique_ids(train, development, test)

    test_texts = {_normalize_text(example.input.text) for example in test}
    clean_train, removed_train = _without_test_duplicates(train, test_texts)
    clean_development, removed_development = _without_test_duplicate_examples(
        development, test_texts
    )
    removed_ids = tuple([*removed_train, *removed_development])

    question_hash = _hash_value(question.model_dump(mode="json"))
    train_hash = _hash_value(
        [item.model_dump(mode="json") for item in clean_train]
    )
    development_hash = _hash_value(
        [item.model_dump(mode="json") for item in clean_development]
    )
    test_hash = _hash_value([item.model_dump(mode="json") for item in test])
    removed_duplicates_hash = _hash_value(list(removed_ids))
    lineage_values = {
        "dataset_id": BANKING77_DATASET_ID,
        "config": BANKING77_CONFIG,
        "revision": BANKING77_REVISION,
        "question_hash": question_hash,
        "train_hash": train_hash,
        "development_hash": development_hash,
        "test_hash": test_hash,
        "removed_duplicates_hash": removed_duplicates_hash,
    }
    lineage = Banking77Lineage(
        **lineage_values,
        dataset_hash=_hash_value(lineage_values),
    )
    return Banking77Dataset(
        train_inputs=tuple(clean_train),
        development_examples=tuple(clean_development),
        test_examples=tuple(test),
        removed_duplicate_ids=removed_ids,
        lineage=lineage,
    )


def _expected_question() -> Banking77Question:
    """Build a fresh immutable outer contract for the pinned question.

    Returns:
        The exact question and criteria at the pinned source revision.
    """
    return Banking77Question(
        instructions=BANKING77_INSTRUCTIONS,
        criteria=dict(BANKING77_CRITERIA),
    )


def _parse_inputs(
    rows: Sequence[Mapping[str, Any]],
    split: str,
    expected_question: Banking77Question,
) -> list[Banking77TeacherInput]:
    """Parse source rows without retaining their human labels.

    Args:
        rows: Raw records from one source split.
        split: Expected split metadata for every row.
        expected_question: Exact pinned choice question.

    Returns:
        Parsed model-visible inputs with no gold-label field.
    """
    return [_parse_input(row, split, expected_question) for row in rows]


def _parse_gold_examples(
    rows: Sequence[Mapping[str, Any]],
    split: str,
    expected_question: Banking77Question,
) -> list[Banking77GoldExample]:
    """Parse the held-out split while keeping gold labels isolated.

    Args:
        rows: Raw held-out source records.
        split: Expected validation or test split metadata.
        expected_question: Exact pinned choice question.

    Returns:
        Parsed evaluation inputs paired with human gold labels.

    Raises:
        DataContractError: If a gold label is outside the pinned taxonomy.
    """
    examples: list[Banking77GoldExample] = []
    for row in rows:
        input_record = _parse_input(row, split, expected_question)
        label = row.get("label")
        if not isinstance(label, str) or label not in BANKING77_CRITERIA:
            raise DataContractError(
                f"Banking77 row {input_record.example_id!r} has an invalid "
                "gold label"
            )
        examples.append(
            Banking77GoldExample(input=input_record, gold_label=label)
        )
    return examples


def _parse_input(
    row: Mapping[str, Any],
    split: str,
    expected_question: Banking77Question,
) -> Banking77TeacherInput:
    """Validate one pinned wire record and return model-visible fields.

    Args:
        row: Raw source record.
        split: Expected split metadata.
        expected_question: Exact pinned choice question.

    Returns:
        A label-free model input.

    Raises:
        DataContractError: If source metadata or model-visible fields drift.
    """
    example_id = row.get("id")
    if not isinstance(example_id, str) or not example_id:
        raise DataContractError("Banking77 row has no valid ID")
    if row.get("source") != BANKING77_CONFIG:
        raise DataContractError(
            f"Banking77 row {example_id!r} has the wrong source"
        )
    if row.get("primitive") != "choice" or row.get("split") != split:
        raise DataContractError(
            f"Banking77 row {example_id!r} has invalid split metadata"
        )

    text = _decode_json_string(row.get("state"), "state", example_id)
    if not text:
        raise DataContractError(f"Banking77 row {example_id!r} has empty text")
    question_value = _decode_question(row.get("question"), example_id)
    if question_value != expected_question.model_dump(mode="json"):
        raise DataContractError(
            f"Banking77 row {example_id!r} changed the pinned question or "
            "77-label taxonomy"
        )
    return Banking77TeacherInput(
        example_id=example_id,
        text=text,
        question=expected_question,
    )


def _decode_json_string(value: Any, field: str, example_id: str) -> str:
    """Decode a wire field whose JSON value must be a string.

    Args:
        value: Raw JSON-encoded value.
        field: Field name used in validation errors.
        example_id: Source row identity used in validation errors.

    Returns:
        The decoded string.

    Raises:
        DataContractError: If the value is not valid JSON encoding a string.
    """
    if not isinstance(value, str):
        raise DataContractError(
            f"Banking77 row {example_id!r} has an invalid {field}"
        )
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise DataContractError(
            f"Banking77 row {example_id!r} has malformed JSON in {field}"
        ) from exc
    if not isinstance(decoded, str):
        raise DataContractError(
            f"Banking77 row {example_id!r} has a non-string {field}"
        )
    return decoded


def _decode_question(value: Any, example_id: str) -> dict[str, Any]:
    """Decode and type-check one JSON-encoded choice question.

    Args:
        value: Raw JSON-encoded question.
        example_id: Source row identity used in validation errors.

    Returns:
        The decoded question object.

    Raises:
        DataContractError: If the question is not valid JSON object data.
    """
    if not isinstance(value, str):
        raise DataContractError(
            f"Banking77 row {example_id!r} has an invalid question"
        )
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise DataContractError(
            f"Banking77 row {example_id!r} has malformed question JSON"
        ) from exc
    if not isinstance(decoded, dict):
        raise DataContractError(
            f"Banking77 row {example_id!r} has a non-object question"
        )
    return decoded


def _validate_unique_ids(
    train: Sequence[Banking77TeacherInput],
    development: Sequence[Banking77GoldExample],
    test: Sequence[Banking77GoldExample],
) -> None:
    """Reject IDs repeated within or across source splits.

    Args:
        train: Parsed training inputs.
        development: Parsed development inputs with isolated gold labels.
        test: Parsed held-out evaluation examples.

    Raises:
        DataContractError: If an ID appears more than once.
    """
    ids = [item.example_id for item in train]
    ids.extend(item.input.example_id for item in development)
    ids.extend(item.input.example_id for item in test)
    if len(ids) != len(set(ids)):
        raise DataContractError("Banking77 source contains duplicate IDs")


def _without_test_duplicates(
    inputs: Sequence[Banking77TeacherInput], test_texts: set[str]
) -> tuple[list[Banking77TeacherInput], list[str]]:
    """Remove training inputs whose normalized text occurs in test.

    Args:
        inputs: Training inputs to inspect.
        test_texts: Normalized held-out texts.

    Returns:
        The retained inputs and removed source IDs, both in source order.
    """
    kept: list[Banking77TeacherInput] = []
    removed: list[str] = []
    for item in inputs:
        if _normalize_text(item.text) in test_texts:
            removed.append(item.example_id)
        else:
            kept.append(item)
    return kept, removed


def _without_test_duplicate_examples(
    examples: Sequence[Banking77GoldExample], test_texts: set[str]
) -> tuple[list[Banking77GoldExample], list[str]]:
    """Remove validation examples whose normalized text occurs in test.

    Args:
        examples: Validation inputs paired with isolated human labels.
        test_texts: Normalized final-test texts.

    Returns:
        Retained complete examples and removed source IDs in source order.
    """
    kept: list[Banking77GoldExample] = []
    removed: list[str] = []
    for example in examples:
        if _normalize_text(example.input.text) in test_texts:
            removed.append(example.input.example_id)
        else:
            kept.append(example)
    return kept, removed


def _normalize_text(text: str) -> str:
    """Normalize Unicode, case, and whitespace for duplicate detection.

    Args:
        text: Exact source message.

    Returns:
        A comparison-only representation of the message.
    """
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(normalized.split())


def _hash_value(value: Any) -> str:
    """Hash a value through deterministic UTF-8 JSON serialization.

    Args:
        value: JSON-serializable lineage value.

    Returns:
        A prefixed SHA-256 digest.
    """
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"
