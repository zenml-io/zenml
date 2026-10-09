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

"""A reloadable lexical student for multiclass teacher decisions."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score


@dataclass(frozen=True)
class TeacherSupervision:
    """One model input and its teacher supervision.

    Exactly one of ``teacher_label`` and ``teacher_distribution`` must be set.
    Human labels are deliberately absent from this training contract.
    """

    example_id: str
    text: str
    teacher_label: str | None = None
    teacher_distribution: Mapping[str, float] | None = None


@dataclass(frozen=True)
class MulticlassMetrics:
    """Human-grounded quality and teacher-imitation measurements."""

    evaluated_count: int
    accuracy: float
    macro_f1: float
    negative_log_likelihood: float
    brier_score: float
    top_label_ece: float
    teacher_agreement: float


class DistributionPredictor(Protocol):
    """Any student that returns a complete taxonomy distribution per input."""

    @property
    def taxonomy(self) -> tuple[str, ...]:
        """Ordered labels the student predicts over."""

    def predict_distributions(
        self, texts: Sequence[str]
    ) -> list[dict[str, float]]:
        """Predict one probability per taxonomy label for each input."""


@dataclass(frozen=True)
class LexicalMulticlassStudent:
    """Word and character TF-IDF features with a softmax linear head."""

    taxonomy: tuple[str, ...]
    word_vocabulary: dict[str, int]
    word_idf: tuple[float, ...]
    char_vocabulary: dict[str, int]
    char_idf: tuple[float, ...]
    coefficients: tuple[tuple[float, ...], ...]
    intercepts: tuple[float, ...]
    training_example_ids: tuple[str, ...]

    def predict_distributions(
        self, texts: Sequence[str]
    ) -> list[dict[str, float]]:
        """Predict a complete taxonomy distribution for each input.

        Args:
            texts: Text inputs in inference order.

        Returns:
            One label-to-probability mapping per input.
        """
        if not texts:
            return []
        matrix = _transform_texts(texts, self)
        logits = matrix @ np.asarray(self.coefficients, dtype=float).T
        logits = np.asarray(logits) + np.asarray(self.intercepts, dtype=float)
        probabilities = _softmax(logits)
        return [
            {
                label: float(probability)
                for label, probability in zip(self.taxonomy, row)
            }
            for row in probabilities
        ]

    def predict(self, texts: Sequence[str]) -> list[str]:
        """Return the highest-probability label for each input.

        Args:
            texts: Text inputs in inference order.

        Returns:
            Highest-probability labels in inference order.
        """
        return [
            max(distribution, key=distribution.__getitem__)
            for distribution in self.predict_distributions(texts)
        ]


def train_lexical_student(
    examples: Sequence[TeacherSupervision],
    *,
    taxonomy: Sequence[str],
    max_word_features: int = 20_000,
    max_char_features: int = 30_000,
    epochs: int = 30,
    learning_rate: float = 0.5,
    l2: float = 1e-4,
) -> LexicalMulticlassStudent:
    """Train a multiclass student only from teacher supervision.

    Distribution targets optimize the full soft-label cross entropy. Hard
    labels are represented as one-hot distributions using the same path.

    Args:
        examples: Inputs paired with teacher hard labels or distributions.
        taxonomy: Complete ordered set of allowed labels.
        max_word_features: Maximum word unigram/bigram feature count.
        max_char_features: Maximum character 3-5 gram feature count.
        epochs: Full-batch deterministic gradient updates.
        learning_rate: Initial gradient-descent learning rate.
        l2: L2 penalty applied to the linear coefficients.

    Returns:
        A self-contained lexical student.

    Raises:
        ValueError: If taxonomy, examples, targets, or hyperparameters are
            invalid.
    """
    labels = _validate_taxonomy(taxonomy)
    if not examples:
        raise ValueError(
            "training requires at least one teacher-labeled input"
        )
    if len({example.example_id for example in examples}) != len(examples):
        raise ValueError("training example IDs must be unique")
    if any(
        not example.example_id or not example.text.strip()
        for example in examples
    ):
        raise ValueError("training example IDs and text must be nonempty")
    if epochs <= 0 or learning_rate <= 0.0 or l2 < 0.0:
        raise ValueError("training hyperparameters are invalid")

    targets: np.ndarray = np.asarray(
        [_target_row(example, labels) for example in examples], dtype=float
    )
    texts = [example.text for example in examples]
    word_vectorizer, char_vectorizer, matrix = _fit_vectorizers(
        texts,
        max_word_features=max_word_features,
        max_char_features=max_char_features,
    )
    if all(example.teacher_label is not None for example in examples):
        coefficients, intercepts = _fit_hard_label_head(
            matrix,
            targets,
            class_count=len(labels),
        )
    else:
        coefficients, intercepts = _fit_softmax_head(
            matrix,
            targets,
            epochs=epochs,
            learning_rate=learning_rate,
            l2=l2,
        )
    return LexicalMulticlassStudent(
        taxonomy=labels,
        word_vocabulary={
            term: int(index)
            for term, index in word_vectorizer.vocabulary_.items()
        },
        word_idf=tuple(float(value) for value in word_vectorizer.idf_),
        char_vocabulary={
            term: int(index)
            for term, index in char_vectorizer.vocabulary_.items()
        },
        char_idf=tuple(float(value) for value in char_vectorizer.idf_),
        coefficients=tuple(
            tuple(float(value) for value in row) for row in coefficients
        ),
        intercepts=tuple(float(value) for value in intercepts),
        training_example_ids=tuple(example.example_id for example in examples),
    )


def validate_rung_sizes(
    rung_sizes: Sequence[int], *, available: int
) -> tuple[int, ...]:
    """Check that rung sizes are strictly increasing, usable prefixes.

    Args:
        rung_sizes: Requested training prefix sizes.
        available: Number of ordered training examples.

    Returns:
        The validated sizes as a tuple.

    Raises:
        ValueError: If rung sizes are empty, unordered, duplicated,
            non-positive, or exceed the available examples.
    """
    sizes = tuple(rung_sizes)
    if (
        not sizes
        or any(isinstance(size, bool) or size <= 0 for size in sizes)
        or tuple(sorted(set(sizes))) != sizes
        or sizes[-1] > available
    ):
        raise ValueError(
            "rung sizes must be unique increasing positive prefixes within "
            "the available examples"
        )
    return sizes


def train_nested_rungs(
    examples: Sequence[TeacherSupervision],
    *,
    taxonomy: Sequence[str],
    rung_sizes: Sequence[int],
    **training_kwargs: Any,
) -> dict[int, LexicalMulticlassStudent]:
    """Train learning-curve rungs on strictly nested input prefixes.

    Args:
        examples: Deterministically ordered teacher-supervised inputs.
        taxonomy: Complete ordered set of allowed labels.
        rung_sizes: Increasing positive prefix sizes.
        **training_kwargs: Options forwarded to ``train_lexical_student``.

    Returns:
        Models keyed by their training-example count.
    """
    sizes = validate_rung_sizes(rung_sizes, available=len(examples))
    return {
        size: train_lexical_student(
            examples[:size], taxonomy=taxonomy, **training_kwargs
        )
        for size in sizes
    }


def evaluate_student(
    student: DistributionPredictor,
    *,
    texts: Sequence[str],
    human_labels: Sequence[str],
    teacher_labels: Sequence[str],
    ece_bins: int = 10,
) -> MulticlassMetrics:
    """Evaluate student correctness separately from teacher agreement.

    Args:
        student: Trained lexical or fine-tuned student.
        texts: Held-out inputs.
        human_labels: Held-out human ground truth.
        teacher_labels: Teacher top labels for those same inputs.
        ece_bins: Equal-width confidence bins for top-label ECE.

    Returns:
        Multiclass correctness, calibration, and imitation metrics.

    Raises:
        ValueError: If inputs are empty, lengths differ, labels are unknown,
            or ``ece_bins`` is invalid.
    """
    count = len(texts)
    if count == 0:
        raise ValueError("evaluation requires at least one held-out input")
    if len(human_labels) != count or len(teacher_labels) != count:
        raise ValueError(
            "evaluation inputs and labels must have equal lengths"
        )
    if ece_bins <= 0:
        raise ValueError("ece_bins must be positive")
    known = set(student.taxonomy)
    if any(label not in known for label in (*human_labels, *teacher_labels)):
        raise ValueError("evaluation contains a label outside the taxonomy")

    distributions = student.predict_distributions(texts)
    probabilities = np.asarray(
        [
            [distribution[label] for label in student.taxonomy]
            for distribution in distributions
        ]
    )
    predictions = [
        student.taxonomy[index] for index in probabilities.argmax(axis=1)
    ]
    label_indices = {
        label: index for index, label in enumerate(student.taxonomy)
    }
    truth_indices = np.asarray(
        [label_indices[label] for label in human_labels]
    )
    truth_matrix = np.eye(len(student.taxonomy))[truth_indices]
    true_probabilities = probabilities[np.arange(count), truth_indices]

    return MulticlassMetrics(
        evaluated_count=count,
        accuracy=float(accuracy_score(human_labels, predictions)),
        macro_f1=float(
            f1_score(
                human_labels,
                predictions,
                labels=list(student.taxonomy),
                average="macro",
                zero_division=0,
            )
        ),
        negative_log_likelihood=float(
            -np.log(np.clip(true_probabilities, 1e-15, 1.0)).mean()
        ),
        brier_score=float(
            np.square(probabilities - truth_matrix).sum(axis=1).mean()
        ),
        top_label_ece=_top_label_ece(
            probabilities.max(axis=1),
            np.asarray(predictions) == np.asarray(human_labels),
            bins=ece_bins,
        ),
        teacher_agreement=float(accuracy_score(teacher_labels, predictions)),
    )


def save_lexical_student(
    path: Path, student: LexicalMulticlassStudent
) -> None:
    """Save a model as validated, non-executable JSON.

    Args:
        path: Destination JSON path.
        student: Trained student to serialize.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1",
        "model_type": "word-char-tfidf-softmax",
        "taxonomy": student.taxonomy,
        "word_vocabulary": student.word_vocabulary,
        "word_idf": student.word_idf,
        "char_vocabulary": student.char_vocabulary,
        "char_idf": student.char_idf,
        "coefficients": student.coefficients,
        "intercepts": student.intercepts,
        "training_example_ids": student.training_example_ids,
    }
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def load_lexical_student(path: Path) -> LexicalMulticlassStudent:
    """Load a lexical student from strictly validated JSON.

    Args:
        path: Source JSON path.

    Returns:
        Validated lexical student.

    Raises:
        ValueError: If the file cannot be read or contains invalid state.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("could not read lexical student JSON") from exc
    expected = {
        "schema_version",
        "model_type",
        "taxonomy",
        "word_vocabulary",
        "word_idf",
        "char_vocabulary",
        "char_idf",
        "coefficients",
        "intercepts",
        "training_example_ids",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected
        or payload["schema_version"] != "1"
        or payload["model_type"] != "word-char-tfidf-softmax"
    ):
        raise ValueError("file does not contain a supported lexical student")
    try:
        student = LexicalMulticlassStudent(
            taxonomy=_validate_taxonomy(payload["taxonomy"]),
            word_vocabulary=_load_vocabulary(payload["word_vocabulary"]),
            word_idf=_load_float_vector(payload["word_idf"], "word IDF"),
            char_vocabulary=_load_vocabulary(payload["char_vocabulary"]),
            char_idf=_load_float_vector(payload["char_idf"], "character IDF"),
            coefficients=tuple(
                _load_float_vector(row, "coefficient row")
                for row in payload["coefficients"]
            ),
            intercepts=_load_float_vector(payload["intercepts"], "intercepts"),
            training_example_ids=_load_string_vector(
                payload["training_example_ids"], "training example IDs"
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("lexical student state is invalid") from exc
    _validate_student_state(student)
    return student


def _fit_vectorizers(
    texts: Sequence[str], *, max_word_features: int, max_char_features: int
) -> tuple[TfidfVectorizer, TfidfVectorizer, sparse.csr_matrix]:
    """Fit both feature families on the current training rung only.

    Args:
        texts: Training-rung text.
        max_word_features: Maximum word feature count.
        max_char_features: Maximum character feature count.

    Returns:
        Fitted word and character vectorizers and their joined matrix.

    Raises:
        ValueError: If training text produces an empty vocabulary.
    """
    word = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        max_features=max_word_features,
        sublinear_tf=True,
        dtype=np.float64,
    )
    char = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        max_features=max_char_features,
        sublinear_tf=True,
        dtype=np.float64,
    )
    try:
        word_matrix = word.fit_transform(texts)
        char_matrix = char.fit_transform(texts)
    except ValueError as exc:
        raise ValueError(
            "training text produced an empty TF-IDF vocabulary"
        ) from exc
    return word, char, sparse.hstack([word_matrix, char_matrix], format="csr")


def _fit_softmax_head(
    matrix: sparse.csr_matrix,
    targets: np.ndarray,
    *,
    epochs: int,
    learning_rate: float,
    l2: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Optimize soft-label cross entropy with deterministic full batches.

    Args:
        matrix: Sparse training feature matrix.
        targets: Normalized target distributions.
        epochs: Number of full-batch updates.
        learning_rate: Initial learning rate.
        l2: L2 coefficient penalty.

    Returns:
        Fitted coefficient matrix and intercept vector.
    """
    example_count, feature_count = matrix.shape
    class_count = targets.shape[1]
    coefficients = np.zeros((class_count, feature_count), dtype=float)
    intercepts = np.zeros(class_count, dtype=float)
    for epoch in range(epochs):
        probabilities = _softmax(matrix @ coefficients.T + intercepts)
        residual = probabilities - targets
        step = learning_rate / math.sqrt(epoch + 1.0)
        coefficient_gradient = np.asarray(residual.T @ matrix) / example_count
        coefficient_gradient += l2 * coefficients
        intercept_gradient = residual.mean(axis=0)
        coefficients -= step * coefficient_gradient
        intercepts -= step * intercept_gradient
    return coefficients, intercepts


def _fit_hard_label_head(
    matrix: sparse.csr_matrix,
    targets: np.ndarray,
    *,
    class_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit the strong deterministic baseline for hard teacher labels.

    Args:
        matrix: Sparse training feature matrix.
        targets: One-hot teacher targets.
        class_count: Complete taxonomy size.

    Returns:
        Coefficients and intercepts aligned to the complete taxonomy.
    """
    target_indices = targets.argmax(axis=1)
    classifier = LogisticRegression(
        C=4.0,
        max_iter=500,
        random_state=0,
        solver="lbfgs",
    )
    classifier.fit(matrix, target_indices)
    coefficients = np.zeros((class_count, matrix.shape[1]), dtype=np.float64)
    intercepts = np.full(class_count, -30.0, dtype=np.float64)
    if classifier.coef_.shape[0] == 1:
        negative_index, positive_index = map(int, classifier.classes_)
        coefficients[negative_index] = 0.0
        intercepts[negative_index] = 0.0
        coefficients[positive_index] = classifier.coef_[0]
        intercepts[positive_index] = classifier.intercept_[0]
    else:
        for source_index, target_index in enumerate(classifier.classes_):
            coefficients[int(target_index)] = classifier.coef_[source_index]
            intercepts[int(target_index)] = classifier.intercept_[source_index]
    return coefficients, intercepts


def _transform_texts(
    texts: Sequence[str], student: LexicalMulticlassStudent
) -> sparse.csr_matrix:
    """Recreate fixed-vocabulary feature transforms from JSON state.

    Args:
        texts: Inference text.
        student: Student containing frozen TF-IDF state.

    Returns:
        Joined sparse word and character feature matrix.
    """
    word = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        vocabulary=student.word_vocabulary,
        sublinear_tf=True,
        dtype=np.float64,
    )
    char = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        vocabulary=student.char_vocabulary,
        sublinear_tf=True,
        dtype=np.float64,
    )
    word.idf_ = np.asarray(student.word_idf)
    char.idf_ = np.asarray(student.char_idf)
    return sparse.hstack(
        [word.transform(texts), char.transform(texts)], format="csr"
    )


def _target_row(
    example: TeacherSupervision, taxonomy: tuple[str, ...]
) -> tuple[float, ...]:
    """Validate and normalize one hard or soft teacher target.

    Args:
        example: Teacher-supervised example.
        taxonomy: Ordered allowed labels.

    Returns:
        Normalized target probabilities in taxonomy order.

    Raises:
        ValueError: If the target is missing, ambiguous, unknown, or invalid.
    """
    has_label = example.teacher_label is not None
    has_distribution = example.teacher_distribution is not None
    if has_label == has_distribution:
        raise ValueError(
            f"example {example.example_id!r} must have exactly one teacher target"
        )
    if example.teacher_label is not None:
        if example.teacher_label not in taxonomy:
            raise ValueError("teacher label is outside the taxonomy")
        return tuple(
            float(label == example.teacher_label) for label in taxonomy
        )
    assert example.teacher_distribution is not None
    unknown = set(example.teacher_distribution) - set(taxonomy)
    if unknown:
        raise ValueError(
            "teacher distribution contains labels outside the taxonomy"
        )
    values = tuple(
        float(example.teacher_distribution.get(label, 0.0))
        for label in taxonomy
    )
    if any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError(
            "teacher distribution contains an invalid probability"
        )
    total = sum(values)
    if total <= 0.0:
        raise ValueError("teacher distribution has no probability mass")
    return tuple(value / total for value in values)


def _validate_taxonomy(taxonomy: Sequence[str]) -> tuple[str, ...]:
    """Return a nonempty, ordered, unique label taxonomy.

    Args:
        taxonomy: Candidate ordered label sequence.

    Returns:
        Validated taxonomy tuple.

    Raises:
        ValueError: If fewer than two unique nonempty labels are provided.
    """
    if isinstance(taxonomy, (str, bytes)):
        raise ValueError("taxonomy must be a sequence of labels")
    labels = tuple(taxonomy)
    if (
        len(labels) < 2
        or len(set(labels)) != len(labels)
        or any(not isinstance(label, str) or not label for label in labels)
    ):
        raise ValueError("taxonomy must contain at least two unique labels")
    return labels


def _softmax(logits: Any) -> np.ndarray:
    """Compute stable row-wise softmax probabilities.

    Args:
        logits: Two-dimensional numeric values.

    Returns:
        Normalized row-wise probabilities.
    """
    values = np.asarray(logits, dtype=float)
    values -= values.max(axis=1, keepdims=True)
    exponentials = np.exp(values)
    probabilities: np.ndarray = exponentials / exponentials.sum(
        axis=1, keepdims=True
    )
    return probabilities


def _top_label_ece(
    confidences: np.ndarray, correctness: np.ndarray, *, bins: int
) -> float:
    """Compute equal-width top-label expected calibration error.

    Args:
        confidences: Highest predicted probability for each row.
        correctness: Whether each top-label prediction was correct.
        bins: Number of equal-width confidence bins.

    Returns:
        Weighted absolute confidence-versus-accuracy gap.
    """
    edges = np.linspace(0.0, 1.0, bins + 1)
    result = 0.0
    for index in range(bins):
        upper_inclusive = index == bins - 1
        members = (confidences >= edges[index]) & (
            confidences <= edges[index + 1]
            if upper_inclusive
            else confidences < edges[index + 1]
        )
        if members.any():
            result += float(members.mean()) * abs(
                float(correctness[members].mean())
                - float(confidences[members].mean())
            )
    return result


def _load_vocabulary(value: object) -> dict[str, int]:
    """Validate a contiguous TF-IDF vocabulary loaded from JSON.

    Args:
        value: Untrusted parsed JSON value.

    Returns:
        Validated term-to-index mapping.

    Raises:
        ValueError: If the vocabulary is empty or noncontiguous.
    """
    if (
        not isinstance(value, dict)
        or not value
        or not all(
            isinstance(term, str)
            and term
            and isinstance(index, int)
            and not isinstance(index, bool)
            for term, index in value.items()
        )
        or sorted(value.values()) != list(range(len(value)))
    ):
        raise ValueError("invalid TF-IDF vocabulary")
    return value


def _load_float_vector(value: object, name: str) -> tuple[float, ...]:
    """Validate a nonempty finite numeric vector loaded from JSON.

    Args:
        value: Untrusted parsed JSON value.
        name: Field name used in validation errors.

    Returns:
        Validated finite float tuple.

    Raises:
        ValueError: If the value is not a nonempty finite numeric list.
    """
    if (
        not isinstance(value, list)
        or not value
        or any(
            not isinstance(item, (int, float))
            or isinstance(item, bool)
            or not math.isfinite(float(item))
            for item in value
        )
    ):
        raise ValueError(f"invalid {name}")
    return tuple(float(item) for item in value)


def _load_string_vector(value: object, name: str) -> tuple[str, ...]:
    """Validate a nonempty string vector loaded from JSON.

    Args:
        value: Untrusted parsed JSON value.
        name: Field name used in validation errors.

    Returns:
        Validated nonempty string tuple.

    Raises:
        ValueError: If the value is not a nonempty string list.
    """
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise ValueError(f"invalid {name}")
    return tuple(value)


def _validate_student_state(student: LexicalMulticlassStudent) -> None:
    """Reject malformed or dimensionally inconsistent serialized state.

    Args:
        student: Deserialized student to validate.

    Raises:
        ValueError: If the IDF, linear head, or training identity is invalid.
    """
    feature_count = len(student.word_vocabulary) + len(student.char_vocabulary)
    if len(student.word_idf) != len(student.word_vocabulary) or len(
        student.char_idf
    ) != len(student.char_vocabulary):
        raise ValueError("IDF width does not match vocabulary")
    if any(value <= 0.0 for value in (*student.word_idf, *student.char_idf)):
        raise ValueError("IDF values must be positive")
    if (
        len(student.coefficients) != len(student.taxonomy)
        or any(len(row) != feature_count for row in student.coefficients)
        or len(student.intercepts) != len(student.taxonomy)
        or not student.training_example_ids
        or len(set(student.training_example_ids))
        != len(student.training_example_ids)
        or any(
            not isinstance(example_id, str) or not example_id
            for example_id in student.training_example_ids
        )
    ):
        raise ValueError("linear head or training identity is invalid")
