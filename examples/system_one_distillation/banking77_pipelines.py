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

"""ZenML pipelines for the Banking77 open-teacher experiment."""

import dataclasses
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any, NamedTuple

from examples.system_one_distillation.banking77_data import (
    Banking77GoldCohort,
    Banking77GoldExample,
    Banking77InputCohort,
    Banking77Lineage,
    Banking77TeacherInput,
    load_banking77_dataset,
)
from examples.system_one_distillation.banking77_model import (
    LexicalMulticlassStudent,
    MulticlassMetrics,
    TeacherSupervision,
    evaluate_student,
    train_nested_rungs,
    validate_rung_sizes,
)
from examples.system_one_distillation.banking77_open_teacher import (
    Banking77OpenTeacherLabel,
    OpenTeacherRun,
    label_with_open_teacher,
)
from examples.system_one_distillation.contracts import ContractModel
from pydantic import Field

from zenml import pipeline, step
from zenml.client import Client

DEFAULT_RUNG_SIZES = (250, 500, 1_000, 2_000, 4_000, 7_999)
TEACHER_SHARD_COUNT = 4


class Banking77TeacherEvaluation(ContractModel):
    """Human-grounded quality and runtime of the open teacher."""

    evaluated_count: int = Field(ge=1)
    accuracy: float = Field(ge=0.0, le=1.0)
    macro_f1: float = Field(ge=0.0, le=1.0)
    negative_log_likelihood: float = Field(ge=0.0)
    brier_score: float = Field(ge=0.0)
    elapsed_seconds: float = Field(ge=0.0)
    decisions_per_second: float = Field(ge=0.0)


class Banking77RungResult(ContractModel):
    """Held-out result for one predetermined training-data rung."""

    training_size: int = Field(ge=1)
    human_accuracy: float = Field(ge=0.0, le=1.0)
    human_macro_f1: float = Field(ge=0.0, le=1.0)
    negative_log_likelihood: float = Field(ge=0.0)
    brier_score: float = Field(ge=0.0)
    top_label_ece: float = Field(ge=0.0, le=1.0)
    teacher_agreement: float = Field(ge=0.0, le=1.0)


class Banking77DistillationReport(ContractModel):
    """Complete lineage, throughput, and fixed-rung experiment result."""

    dataset_id: str = Field(min_length=1)
    dataset_config: str = Field(min_length=1)
    dataset_revision: str = Field(min_length=1)
    dataset_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    teacher_model_id: str = Field(min_length=1)
    teacher_model_revision: str = Field(min_length=1)
    teacher_code_revision: str = Field(min_length=1)
    teacher_decision_count: int = Field(ge=1)
    teacher_inference_wall_seconds: float = Field(ge=0.0)
    teacher_inference_decisions_per_second: float = Field(ge=0.0)
    teacher_worker_count: int = Field(ge=1)
    teacher_worker_inference_seconds: tuple[float, ...]
    teacher_total_worker_inference_seconds: float = Field(ge=0.0)
    teacher_batch_size: int = Field(ge=1)
    teacher_prefix_cache: bool
    teacher_requested_gpu: str = Field(min_length=1)
    training_example_count: int = Field(ge=1)
    test_example_count: int = Field(ge=1)
    removed_duplicate_count: int = Field(ge=0)
    teacher_human_metrics: Banking77TeacherEvaluation
    rung_results: tuple[Banking77RungResult, ...]
    final_rung_size: int = Field(ge=1)


class Banking77QwenRungResult(Banking77RungResult):
    """Held-out result and training record for one Qwen student rung."""

    epochs: int = Field(ge=1)
    optimizer_steps: int = Field(ge=1)
    truncated_count: int = Field(ge=0)
    training_seconds: float = Field(ge=0.0)
    test_inference_seconds: float = Field(ge=0.0)


class Banking77QwenStudentReport(ContractModel):
    """Fine-tuned small-LLM students trained on the stored teacher labels."""

    student_model_id: str = Field(min_length=1)
    student_model_revision: str = Field(min_length=1)
    student_parameter_count: int = Field(ge=1)
    requested_gpu: str = Field(min_length=1)
    training_recipe: dict[str, Any]
    teacher_model_id: str = Field(min_length=1)
    teacher_model_revision: str = Field(min_length=1)
    training_example_count: int = Field(ge=1)
    test_example_count: int = Field(ge=1)
    teacher_human_metrics: Banking77TeacherEvaluation
    rung_results: tuple[Banking77QwenRungResult, ...]
    final_rung_size: int = Field(ge=1)
    final_model_bytes: int = Field(ge=1)


class Banking77StudentComparisonRow(ContractModel):
    """One model's human-grounded result at one amount of teacher labels."""

    model: str = Field(min_length=1)
    teacher_labels: int | None = Field(default=None, ge=1)
    human_accuracy: float = Field(ge=0.0, le=1.0)
    human_macro_f1: float = Field(ge=0.0, le=1.0)
    teacher_agreement: float | None = Field(default=None, ge=0.0, le=1.0)
    brier_score: float = Field(ge=0.0)


class Banking77StudentComparison(ContractModel):
    """Teacher, lexical student, and Qwen student on the same human labels."""

    test_example_count: int = Field(ge=1)
    rows: tuple[Banking77StudentComparisonRow, ...]


@step
def load_banking77_teacher_pilot(
    evaluation_limit: int = 100,
) -> tuple[
    Annotated[Banking77InputCohort, "teacher_inputs"],
    Annotated[Banking77GoldCohort, "gold_examples"],
    Annotated[Banking77Lineage, "dataset_lineage"],
]:
    """Load a prefix of the pinned validation split for a teacher pilot.

    Args:
        evaluation_limit: Number of held-out examples to evaluate.

    Returns:
        Label-free teacher inputs, isolated gold labels, and data lineage.

    Raises:
        ValueError: If the requested cohort size is invalid.
    """
    dataset = load_banking77_dataset()
    if not 1 <= evaluation_limit <= len(dataset.development_examples):
        raise ValueError("evaluation_limit is outside the validation split")
    gold = dataset.development_examples[:evaluation_limit]
    return (
        Banking77InputCohort(items=tuple(item.input for item in gold)),
        Banking77GoldCohort(items=gold),
        dataset.lineage,
    )


@step
def load_banking77_distillation_data() -> tuple[
    Annotated[Banking77InputCohort, "training_inputs"],
    Annotated[Banking77InputCohort, "test_inputs"],
    Annotated[Banking77GoldCohort, "gold_test_examples"],
    Annotated[Banking77Lineage, "dataset_lineage"],
    Annotated[tuple[str, ...], "removed_duplicate_ids"],
]:
    """Load all label-free training inputs and the untouched gold test split.

    Returns:
        Training inputs, label-free test inputs, isolated gold test records,
        immutable data lineage, and removed train/test duplicate identities.
    """
    dataset = load_banking77_dataset()
    return (
        Banking77InputCohort(items=dataset.train_inputs),
        Banking77InputCohort(
            items=tuple(example.input for example in dataset.test_examples)
        ),
        Banking77GoldCohort(items=dataset.test_examples),
        dataset.lineage,
        dataset.removed_duplicate_ids,
    )


@step
def label_banking77_with_open_teacher(
    inputs: Banking77InputCohort,
    batch_size: int = 32,
    prefix_cache: bool = False,
) -> OpenTeacherRun:
    """Run the pinned open teacher on one label-free ZenML artifact.

    Args:
        inputs: Exact held-out or training messages.
        batch_size: Candidate sequences per GPU batch.
        prefix_cache: Enable experimental request-local prefix reuse.

    Returns:
        Full typed distributions and aggregate runtime evidence.
    """
    return label_with_open_teacher(
        inputs.items, batch_size=batch_size, prefix_cache=prefix_cache
    )


@step
def label_complete_banking77_cohort(
    training_inputs: Banking77InputCohort,
    test_inputs: Banking77InputCohort,
    batch_size: int = 32,
    prefix_cache: bool = False,
) -> OpenTeacherRun:
    """Make one teacher pass over all train and held-out inputs.

    Args:
        training_inputs: Complete label-free training cohort.
        test_inputs: Complete label-free held-out cohort.
        batch_size: Candidate sequences per GPU batch.
        prefix_cache: Enable experimental request-local prefix reuse.

    Returns:
        One run containing every train and test teacher decision.

    Raises:
        ValueError: If train and test identities overlap.
    """
    training_ids = {item.example_id for item in training_inputs.items}
    test_ids = {item.example_id for item in test_inputs.items}
    if training_ids.intersection(test_ids):
        raise ValueError("training and test input identities overlap")
    return label_with_open_teacher(
        (*training_inputs.items, *test_inputs.items),
        batch_size=batch_size,
        prefix_cache=prefix_cache,
    )


@step
def shard_complete_banking77_cohort(
    training_inputs: Banking77InputCohort,
    test_inputs: Banking77InputCohort,
) -> tuple[
    Annotated[Banking77InputCohort, "teacher_shard_1"],
    Annotated[Banking77InputCohort, "teacher_shard_2"],
    Annotated[Banking77InputCohort, "teacher_shard_3"],
    Annotated[Banking77InputCohort, "teacher_shard_4"],
]:
    """Split the complete teacher cohort into four contiguous shards.

    Args:
        training_inputs: Complete label-free training cohort.
        test_inputs: Complete label-free held-out cohort.

    Returns:
        Four nonempty, ordered shards with sizes differing by at most one.

    Raises:
        ValueError: If identities overlap or the cohort is too small.
    """
    combined = (*training_inputs.items, *test_inputs.items)
    identities = [item.example_id for item in combined]
    if len(set(identities)) != len(identities):
        raise ValueError("teacher cohort identities must be unique")
    if len(combined) < TEACHER_SHARD_COUNT:
        raise ValueError("teacher cohort is too small for four shards")
    base_size, remainder = divmod(len(combined), TEACHER_SHARD_COUNT)
    shards: list[tuple[Banking77TeacherInput, ...]] = []
    start = 0
    for index in range(TEACHER_SHARD_COUNT):
        size = base_size + (1 if index < remainder else 0)
        shards.append(tuple(combined[start : start + size]))
        start += size
    return (
        Banking77InputCohort(items=shards[0]),
        Banking77InputCohort(items=shards[1]),
        Banking77InputCohort(items=shards[2]),
        Banking77InputCohort(items=shards[3]),
    )


@step
def merge_open_teacher_shards(
    shard_1: OpenTeacherRun,
    shard_2: OpenTeacherRun,
    shard_3: OpenTeacherRun,
    shard_4: OpenTeacherRun,
) -> OpenTeacherRun:
    """Merge four independently materialized teacher runs in shard order.

    Args:
        shard_1: First teacher run.
        shard_2: Second teacher run.
        shard_3: Third teacher run.
        shard_4: Fourth teacher run.

    Returns:
        One ordered run with aggregate parallel wall-clock throughput.

    Raises:
        ValueError: If shard identities overlap or cache modes differ.
    """
    shards = (shard_1, shard_2, shard_3, shard_4)
    labels = tuple(label for shard in shards for label in shard.labels)
    if len({label.example_id for label in labels}) != len(labels):
        raise ValueError("teacher shards contain duplicate identities")
    prefix_cache_values = {shard.prefix_cache for shard in shards}
    if len(prefix_cache_values) != 1:
        raise ValueError("teacher shards used different prefix-cache modes")
    worker_elapsed = tuple(
        elapsed
        for shard in shards
        for elapsed in (
            shard.worker_elapsed_seconds or (shard.elapsed_seconds,)
        )
    )
    wall_elapsed = max(worker_elapsed)
    return OpenTeacherRun(
        labels=labels,
        elapsed_seconds=wall_elapsed,
        decisions_per_second=(
            len(labels) / wall_elapsed if wall_elapsed else 0.0
        ),
        prefix_cache=shard_1.prefix_cache,
        worker_elapsed_seconds=worker_elapsed,
    )


@step
def evaluate_open_teacher(
    teacher_run: OpenTeacherRun,
    gold_examples: Banking77GoldCohort,
) -> Banking77TeacherEvaluation:
    """Evaluate teacher predictions against isolated human labels.

    Args:
        teacher_run: Open-teacher predictions for the held-out cohort.
        gold_examples: Human labels that never entered teacher inference.

    Returns:
        Accuracy, probability quality, and measured throughput.
    """
    return _evaluate_teacher(teacher_run, gold_examples.items, exact_ids=True)


@step
def distill_banking77_students(
    training_inputs: Banking77InputCohort,
    gold_examples: Banking77GoldCohort,
    teacher_run: OpenTeacherRun,
    dataset_lineage: Banking77Lineage,
    removed_duplicate_ids: tuple[str, ...],
    rung_sizes: tuple[int, ...] = DEFAULT_RUNG_SIZES,
    teacher_batch_size: int = 32,
    teacher_prefix_cache: bool = False,
    teacher_requested_gpu: str = "unspecified",
) -> tuple[
    Annotated[Banking77DistillationReport, "distillation_report"],
    Annotated[LexicalMulticlassStudent, "final_student_model"],
]:
    """Train predetermined nested rungs and evaluate each on untouched gold.

    The largest requested rung is always final, regardless of test performance.

    Args:
        training_inputs: Complete label-free training cohort.
        gold_examples: Untouched held-out inputs and human labels.
        teacher_run: One teacher run covering training and test identities.
        dataset_lineage: Exact pinned dataset identity and content hashes.
        removed_duplicate_ids: Train records removed for matching test text.
        rung_sizes: Predetermined increasing training prefix sizes.
        teacher_batch_size: Candidate sequences per teacher GPU batch.
        teacher_prefix_cache: Whether request-local prefix reuse was enabled.
        teacher_requested_gpu: GPU type requested from the orchestrator.

    Returns:
        Full experiment report and the largest-rung student model.
    """
    data = _student_data(training_inputs, gold_examples, teacher_run)
    students = train_nested_rungs(
        data.supervision, taxonomy=data.taxonomy, rung_sizes=rung_sizes
    )
    results = [
        Banking77RungResult(**_rung_fields(size, data.evaluate(student)))
        for size, student in students.items()
    ]

    final_size = rung_sizes[-1]
    model_id, model_revision, code_revision = _teacher_revisions(
        teacher_run.labels
    )
    worker_elapsed = teacher_run.worker_elapsed_seconds or (
        teacher_run.elapsed_seconds,
    )
    report = Banking77DistillationReport(
        dataset_id=dataset_lineage.dataset_id,
        dataset_config=dataset_lineage.config,
        dataset_revision=dataset_lineage.revision,
        dataset_hash=dataset_lineage.dataset_hash,
        teacher_model_id=model_id,
        teacher_model_revision=model_revision,
        teacher_code_revision=code_revision,
        teacher_decision_count=len(teacher_run.labels),
        teacher_inference_wall_seconds=teacher_run.elapsed_seconds,
        teacher_inference_decisions_per_second=(
            teacher_run.decisions_per_second
        ),
        teacher_worker_count=len(worker_elapsed),
        teacher_worker_inference_seconds=worker_elapsed,
        teacher_total_worker_inference_seconds=sum(worker_elapsed),
        teacher_batch_size=teacher_batch_size,
        teacher_prefix_cache=teacher_prefix_cache,
        teacher_requested_gpu=teacher_requested_gpu,
        training_example_count=len(training_inputs.items),
        test_example_count=len(gold_examples.items),
        removed_duplicate_count=len(removed_duplicate_ids),
        teacher_human_metrics=_evaluate_teacher(
            teacher_run, gold_examples.items, exact_ids=False
        ),
        rung_results=tuple(results),
        final_rung_size=final_size,
    )
    return report, students[final_size]


@step
def distill_banking77_qwen_students(
    training_inputs: Banking77InputCohort,
    gold_examples: Banking77GoldCohort,
    teacher_run: OpenTeacherRun,
    rung_sizes: tuple[int, ...] = DEFAULT_RUNG_SIZES,
    requested_gpu: str = "unspecified",
) -> tuple[
    Annotated[Banking77QwenStudentReport, "qwen_distillation_report"],
    Annotated[Path, "final_qwen_student"],
]:
    """Fine-tune a fresh Qwen student per fixed rung on stored teacher labels.

    Uses the same training order, rung prefixes, and final-rung rule as the
    lexical student. The largest rung is final regardless of test results.

    Args:
        training_inputs: Complete label-free training cohort.
        gold_examples: Untouched held-out inputs and human labels.
        teacher_run: One teacher run covering training and test identities.
        rung_sizes: Predetermined increasing training prefix sizes.
        requested_gpu: GPU type requested from the orchestrator.

    Returns:
        Experiment report and a directory holding the final student weights.

    """
    import tempfile
    import time

    from examples.system_one_distillation.banking77_qwen_student import (
        QwenStudentConfig,
        save_qwen_student,
        train_qwen_student,
    )

    sizes = validate_rung_sizes(
        rung_sizes, available=len(training_inputs.items)
    )
    data = _student_data(training_inputs, gold_examples, teacher_run)
    config = QwenStudentConfig()
    results: list[Banking77QwenRungResult] = []
    student = None
    for size in sizes:
        if student is not None:
            student.release_gpu_memory()
        student, stats = train_qwen_student(
            data.supervision[:size], taxonomy=data.taxonomy, config=config
        )
        started = time.perf_counter()
        metrics = data.evaluate(student)
        results.append(
            Banking77QwenRungResult(
                **_rung_fields(size, metrics),
                epochs=stats.epochs,
                optimizer_steps=stats.optimizer_steps,
                truncated_count=stats.truncated_count,
                training_seconds=stats.training_seconds,
                test_inference_seconds=time.perf_counter() - started,
            )
        )

    output = save_qwen_student(
        student, Path(tempfile.mkdtemp()) / "qwen_student"
    )
    model_id, model_revision, _ = _teacher_revisions(teacher_run.labels)
    report = Banking77QwenStudentReport(
        student_model_id=config.model_id,
        student_model_revision=config.model_revision,
        student_parameter_count=student.parameter_count,
        requested_gpu=requested_gpu,
        training_recipe=dataclasses.asdict(config),
        teacher_model_id=model_id,
        teacher_model_revision=model_revision,
        training_example_count=len(training_inputs.items),
        test_example_count=len(gold_examples.items),
        teacher_human_metrics=_evaluate_teacher(
            teacher_run, gold_examples.items, exact_ids=False
        ),
        rung_results=tuple(results),
        final_rung_size=sizes[-1],
        final_model_bytes=sum(
            path.stat().st_size for path in output.iterdir() if path.is_file()
        ),
    )
    return report, output


@step
def compare_banking77_students(
    lexical_report: Banking77DistillationReport,
    qwen_report: Banking77QwenStudentReport,
) -> Banking77StudentComparison:
    """Put the teacher and both student families on one human-graded table.

    Args:
        lexical_report: Report from the TF-IDF distillation run.
        qwen_report: Report from the Qwen student run.

    Returns:
        One row per model and rung.

    Raises:
        ValueError: If the reports used different teachers or test sets.
    """
    if (
        lexical_report.teacher_model_revision
        != qwen_report.teacher_model_revision
        or lexical_report.test_example_count != qwen_report.test_example_count
    ):
        raise ValueError("student reports do not share a teacher and test set")
    teacher = lexical_report.teacher_human_metrics
    rows = [
        Banking77StudentComparisonRow(
            model=lexical_report.teacher_model_id,
            human_accuracy=teacher.accuracy,
            human_macro_f1=teacher.macro_f1,
            brier_score=teacher.brier_score,
        )
    ]
    for name, report in (
        ("TF-IDF + logistic regression", lexical_report),
        (qwen_report.student_model_id, qwen_report),
    ):
        rows.extend(
            Banking77StudentComparisonRow(
                model=name,
                teacher_labels=result.training_size,
                human_accuracy=result.human_accuracy,
                human_macro_f1=result.human_macro_f1,
                teacher_agreement=result.teacher_agreement,
                brier_score=result.brier_score,
            )
            for result in report.rung_results
        )
    return Banking77StudentComparison(
        test_example_count=lexical_report.test_example_count, rows=tuple(rows)
    )


@pipeline
def banking77_open_teacher_pilot_pipeline(
    evaluation_limit: int = 100,
    batch_size: int = 32,
    prefix_cache: bool = False,
) -> Banking77TeacherEvaluation:
    """Measure the pinned open teacher before purchasing full labels.

    Args:
        evaluation_limit: Number of held-out examples to evaluate.
        batch_size: Candidate sequences per GPU batch.
        prefix_cache: Enable experimental request-local prefix reuse.

    Returns:
        Human-grounded teacher quality and runtime evidence.
    """
    inputs, gold, _ = load_banking77_teacher_pilot(
        evaluation_limit=evaluation_limit
    )
    teacher_run = label_banking77_with_open_teacher(
        inputs=inputs, batch_size=batch_size, prefix_cache=prefix_cache
    )
    return evaluate_open_teacher(teacher_run=teacher_run, gold_examples=gold)


@pipeline
def banking77_distillation_pipeline(
    rung_sizes: tuple[int, ...] = DEFAULT_RUNG_SIZES,
    batch_size: int = 32,
    prefix_cache: bool = False,
    teacher_requested_gpu: str = "H100",
) -> tuple[Banking77DistillationReport, LexicalMulticlassStudent]:
    """Label once, train fixed nested rungs, and return the final student.

    Args:
        rung_sizes: Predetermined increasing training prefix sizes.
        batch_size: Candidate sequences per GPU batch.
        prefix_cache: Enable experimental request-local prefix reuse.
        teacher_requested_gpu: GPU type requested from the orchestrator.

    Returns:
        Complete experiment report and largest-rung student artifact.
    """
    training, test_inputs, gold, lineage, removed_ids = (
        load_banking77_distillation_data()
    )
    shard_1, shard_2, shard_3, shard_4 = shard_complete_banking77_cohort(
        training_inputs=training, test_inputs=test_inputs
    )
    run_1 = label_banking77_with_open_teacher(
        inputs=shard_1,
        batch_size=batch_size,
        prefix_cache=prefix_cache,
        id="label_open_teacher_shard_1",
    )
    run_2 = label_banking77_with_open_teacher(
        inputs=shard_2,
        batch_size=batch_size,
        prefix_cache=prefix_cache,
        id="label_open_teacher_shard_2",
    )
    run_3 = label_banking77_with_open_teacher(
        inputs=shard_3,
        batch_size=batch_size,
        prefix_cache=prefix_cache,
        id="label_open_teacher_shard_3",
    )
    run_4 = label_banking77_with_open_teacher(
        inputs=shard_4,
        batch_size=batch_size,
        prefix_cache=prefix_cache,
        id="label_open_teacher_shard_4",
    )
    teacher_run = merge_open_teacher_shards(
        shard_1=run_1,
        shard_2=run_2,
        shard_3=run_3,
        shard_4=run_4,
    )
    return distill_banking77_students(
        training_inputs=training,
        gold_examples=gold,
        teacher_run=teacher_run,
        dataset_lineage=lineage,
        removed_duplicate_ids=removed_ids,
        rung_sizes=rung_sizes,
        teacher_batch_size=batch_size,
        teacher_prefix_cache=prefix_cache,
        teacher_requested_gpu=teacher_requested_gpu,
    )


@pipeline
def banking77_qwen_student_pipeline(
    source_run_id: str,
    rung_sizes: tuple[int, ...] = DEFAULT_RUNG_SIZES,
    requested_gpu: str = "L40S",
) -> Banking77StudentComparison:
    """Train Qwen students from a finished run's stored teacher labels.

    The teacher never runs here. The cohorts, merged teacher labels, and
    lexical report are the exact artifact versions recorded by the source
    run, so both student families learn from, and are graded on, identical
    data.

    Args:
        source_run_id: Completed ``banking77_distillation_pipeline`` run.
        rung_sizes: Predetermined increasing training prefix sizes.
        requested_gpu: GPU type requested from the orchestrator.

    Returns:
        Teacher, lexical, and Qwen results on the same human test labels.
    """
    source = _source_run_artifacts(source_run_id)
    qwen_report, _ = distill_banking77_qwen_students(
        training_inputs=source["training_inputs"],
        gold_examples=source["gold_test_examples"],
        teacher_run=source["teacher_run"],
        rung_sizes=rung_sizes,
        requested_gpu=requested_gpu,
    )
    return compare_banking77_students(
        lexical_report=source["distillation_report"], qwen_report=qwen_report
    )


def _source_run_artifacts(run_id: str) -> dict[str, Any]:
    """Look up the stored artifact versions a student run reuses.

    Args:
        run_id: Completed ``banking77_distillation_pipeline`` run.

    Returns:
        Artifact versions keyed by their role in the student pipeline.
    """
    steps = Client().get_pipeline_run(run_id).steps
    data_outputs = steps["load_banking77_distillation_data"].regular_outputs
    return {
        "training_inputs": data_outputs["training_inputs"],
        "gold_test_examples": data_outputs["gold_test_examples"],
        "teacher_run": steps["merge_open_teacher_shards"].output,
        "distillation_report": steps[
            "distill_banking77_students"
        ].regular_outputs["distillation_report"],
    }


class _StudentData(NamedTuple):
    """Training supervision and held-out labels shared by every student."""

    taxonomy: tuple[str, ...]
    supervision: list[TeacherSupervision]
    test_texts: list[str]
    human_labels: list[str]
    teacher_test_labels: list[str]

    def evaluate(self, student: Any) -> MulticlassMetrics:
        """Score a student on the held-out human and teacher labels.

        Args:
            student: Any model with ``taxonomy`` and ``predict_distributions``.

        Returns:
            Human-grounded and teacher-agreement metrics.
        """
        return evaluate_student(
            student,
            texts=self.test_texts,
            human_labels=self.human_labels,
            teacher_labels=self.teacher_test_labels,
        )


def _student_data(
    training_inputs: Banking77InputCohort,
    gold_examples: Banking77GoldCohort,
    teacher_run: OpenTeacherRun,
) -> _StudentData:
    """Build the one set of inputs every student trains and is graded on.

    Both student families call this, so they cannot drift apart in how
    teacher labels are split or which labels grade them.

    Args:
        training_inputs: Complete label-free training cohort.
        gold_examples: Untouched held-out inputs and human labels.
        teacher_run: One teacher run covering training and test identities.

    Returns:
        Taxonomy, ordered teacher supervision, and held-out labels.
    """
    train_labels, test_labels = _partition_teacher_labels(
        teacher_run.labels,
        training_inputs=training_inputs.items,
        gold_examples=gold_examples.items,
    )
    return _StudentData(
        taxonomy=_shared_taxonomy(training_inputs.items, gold_examples.items),
        supervision=[
            TeacherSupervision(
                example_id=item.example_id,
                text=item.text,
                teacher_label=train_labels[item.example_id].chosen_label,
            )
            for item in training_inputs.items
        ],
        test_texts=[example.input.text for example in gold_examples.items],
        human_labels=[example.gold_label for example in gold_examples.items],
        teacher_test_labels=[
            test_labels[example.input.example_id].chosen_label
            for example in gold_examples.items
        ],
    )


def _rung_fields(size: int, metrics: MulticlassMetrics) -> dict[str, Any]:
    """Map one rung's metrics onto the shared rung-result fields.

    Args:
        size: Number of teacher-labeled training examples.
        metrics: Held-out metrics for that rung.

    Returns:
        Keyword arguments for ``Banking77RungResult`` and its subclasses.
    """
    return {
        "training_size": size,
        "human_accuracy": metrics.accuracy,
        "human_macro_f1": metrics.macro_f1,
        "negative_log_likelihood": metrics.negative_log_likelihood,
        "brier_score": metrics.brier_score,
        "top_label_ece": metrics.top_label_ece,
        "teacher_agreement": metrics.teacher_agreement,
    }


def _partition_teacher_labels(
    labels: Sequence[Banking77OpenTeacherLabel],
    *,
    training_inputs: Sequence[Banking77TeacherInput],
    gold_examples: Sequence[Banking77GoldExample],
) -> tuple[
    dict[str, Banking77OpenTeacherLabel],
    dict[str, Banking77OpenTeacherLabel],
]:
    """Separate one teacher run by exact train and test identities.

    Args:
        labels: Combined teacher outputs.
        training_inputs: Expected training inputs.
        gold_examples: Expected test examples.

    Returns:
        Training and test labels keyed by example ID.

    Raises:
        ValueError: If labels are duplicated, missing, or unexpected.
    """
    label_by_id = {label.example_id: label for label in labels}
    if len(label_by_id) != len(labels):
        raise ValueError("teacher run contains duplicate example IDs")
    training_ids = {item.example_id for item in training_inputs}
    test_ids = {example.input.example_id for example in gold_examples}
    expected_ids = training_ids.union(test_ids)
    if training_ids.intersection(test_ids) or set(label_by_id) != expected_ids:
        raise ValueError("teacher labels do not exactly cover train and test")
    return (
        {example_id: label_by_id[example_id] for example_id in training_ids},
        {example_id: label_by_id[example_id] for example_id in test_ids},
    )


def _shared_taxonomy(
    training_inputs: Sequence[Banking77TeacherInput],
    gold_examples: Sequence[Banking77GoldExample],
) -> tuple[str, ...]:
    """Validate and return one taxonomy shared by the whole experiment.

    Args:
        training_inputs: Training inputs containing teacher questions.
        gold_examples: Held-out examples containing teacher questions.

    Returns:
        Ordered taxonomy keys.

    Raises:
        ValueError: If cohorts are empty or taxonomies differ.
    """
    all_inputs = [
        *training_inputs,
        *(example.input for example in gold_examples),
    ]
    if not all_inputs:
        raise ValueError("Banking77 experiment cohorts must not be empty")
    taxonomy = tuple(all_inputs[0].question.criteria)
    if any(tuple(item.question.criteria) != taxonomy for item in all_inputs):
        raise ValueError("Banking77 experiment taxonomies differ")
    return taxonomy


def _teacher_revisions(
    labels: Sequence[Banking77OpenTeacherLabel],
) -> tuple[str, str, str]:
    """Return the single teacher identity shared by all labels.

    Args:
        labels: Teacher labels carrying model and code revisions.

    Returns:
        Model ID, model revision, and code revision.

    Raises:
        ValueError: If labels are empty or contain mixed revisions.
    """
    identities = {
        (label.model_id, label.model_revision, label.code_revision)
        for label in labels
    }
    if len(identities) != 1:
        raise ValueError("teacher labels must share one pinned identity")
    return next(iter(identities))


def _evaluate_teacher(
    teacher_run: OpenTeacherRun,
    gold_examples: Sequence[Banking77GoldExample],
    *,
    exact_ids: bool,
) -> Banking77TeacherEvaluation:
    """Compute teacher quality on an isolated held-out cohort.

    Args:
        teacher_run: Teacher outputs and measured aggregate runtime.
        gold_examples: Human-grounded test records.
        exact_ids: Require the run to contain only held-out IDs.

    Returns:
        Teacher correctness, probability quality, and run throughput.

    Raises:
        ValueError: If held-out labels are missing or identities differ.
    """
    import numpy as np
    from sklearn.metrics import accuracy_score, f1_score

    label_by_id = {label.example_id: label for label in teacher_run.labels}
    if len(label_by_id) != len(teacher_run.labels):
        raise ValueError("teacher run contains duplicate example IDs")
    gold_by_id = {
        example.input.example_id: example for example in gold_examples
    }
    identities_match = (
        set(label_by_id) == set(gold_by_id)
        if exact_ids
        else set(gold_by_id).issubset(label_by_id)
    )
    if not gold_by_id or not identities_match:
        raise ValueError("teacher and gold example identities differ")
    taxonomy = tuple(gold_examples[0].input.question.criteria)
    label_index = {label: index for index, label in enumerate(taxonomy)}
    gold_labels = [
        gold_by_id[example_id].gold_label for example_id in gold_by_id
    ]
    teacher_labels = [
        label_by_id[example_id].chosen_label for example_id in gold_by_id
    ]
    probabilities = np.asarray(
        [
            [
                label_by_id[example_id].probabilities[label]
                for label in taxonomy
            ]
            for example_id in gold_by_id
        ],
        dtype=float,
    )
    truth = np.zeros_like(probabilities)
    truth[
        np.arange(len(gold_labels)),
        [label_index[label] for label in gold_labels],
    ] = 1.0
    true_probabilities = probabilities[
        np.arange(len(gold_labels)),
        [label_index[label] for label in gold_labels],
    ]
    return Banking77TeacherEvaluation(
        evaluated_count=len(gold_labels),
        accuracy=float(accuracy_score(gold_labels, teacher_labels)),
        macro_f1=float(
            f1_score(
                gold_labels,
                teacher_labels,
                labels=list(taxonomy),
                average="macro",
                zero_division=0,
            )
        ),
        negative_log_likelihood=float(
            -np.log(np.clip(true_probabilities, 1e-15, 1.0)).mean()
        ),
        brier_score=float(np.square(probabilities - truth).sum(axis=1).mean()),
        elapsed_seconds=teacher_run.elapsed_seconds,
        decisions_per_second=teacher_run.decisions_per_second,
    )
