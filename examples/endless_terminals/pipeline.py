"""Run task qualification, agent evaluation, and reports as native ZenML steps."""

import json
from contextlib import nullcontext
from pathlib import Path
from typing import Annotated, Any, Optional

from cloud import KubernetesInference
from config import EvaluationConfig
from dataset import prepare_tasks, sha256
from reporting import render_evaluation_report, summarize_evaluation
from runtime.contract import UPSTREAM_COMMIT
from runtime.models import EndpointModel, FixtureModel
from runtime.runner import run_episode

from zenml import (
    ExternalArtifact,
    get_step_context,
    log_metadata,
    pipeline,
    save_artifact,
    step,
)
from zenml.types import HTMLString


@step(enable_cache=False)
def prepare_evaluation(
    config: EvaluationConfig,
) -> Annotated[dict[str, Any], "qualified_tasks"]:
    """Qualify task images before allocating inference compute.

    Args:
        config: Evaluation settings.

    Returns:
        Pinned tasks with CPU qualification evidence.
    """
    return prepare_tasks(Path(config.data_directory), config.task_ids)


def execute_evaluation(
    prepared: dict[str, Any], config: EvaluationConfig, run_id: str
) -> dict[str, Any]:
    """Evaluate inside a bounded inference session and retain partial evidence.

    Args:
        prepared: Qualified tasks.
        config: Evaluation settings.
        run_id: Unique ZenML pipeline run ID.

    Returns:
        Complete evaluation evidence.

    Raises:
        RuntimeError: Evaluation or cleanup is incomplete.
    """  # noqa: DOC503
    output = Path(config.output_directory) / run_id
    output.mkdir(parents=True, exist_ok=False)
    model_identity = {
        "name": config.model_name,
        "revision": config.model_revision,
        "revision_verified": config.mode == "kubernetes",
    }
    runtime = Path(__file__).parent / "runtime"
    evaluation: dict[str, Any] = {
        "run_id": run_id,
        "mode": "fixture" if config.mode == "fixture" else "model",
        "model": model_identity
        if config.mode != "fixture"
        else {"name": "reference fixture", "revision": "scripted"},
        "dataset_revision": prepared["dataset_revision"],
        "protocol": {
            "max_actions": config.max_actions,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "command_timeout": config.command_timeout,
            "episode_timeout": config.episode_timeout,
            "upstream_commit": UPSTREAM_COMMIT,
            "backend": config.mode,
            "controller_sha256": sha256(Path(__file__)),
            "runtime_sha256": {
                p.name: sha256(p) for p in sorted(runtime.glob("*.py"))
            },
        },
        "task_hashes": {
            t["task_id"]: {
                "files": t["task_file_sha256"],
                "image": t["local_image_id"],
                "protected_sources": t.get("protected_sources", {}),
            }
            for t in prepared["tasks"]
        },
        "episodes": [],
        "status": "failed",
        "cleanup": {"complete": False},
    }
    session = None
    error: Optional[BaseException] = None
    try:
        if config.mode == "kubernetes":
            cloud_config = json.loads(
                Path(str(config.cloud_config_path)).read_text()
            )
            evaluation["protocol"]["serving"] = {
                "image": cloud_config["vllm_image"],
                "controller_sha256": sha256(
                    Path(__file__).parent / "cloud.py"
                ),
            }
            session = KubernetesInference(
                cloud_config,
                {"name": config.model_name, "revision": config.model_revision},
                run_id,
                output / "inference",
            )
        with session if session is not None else nullcontext():
            if session is not None:
                evaluation["inference"] = session.identity
            for task in prepared["tasks"]:
                if (
                    session is not None
                    and session.serving_seconds_remaining
                    < config.episode_timeout + 240
                ):
                    raise RuntimeError(
                        "Serving deadline cannot accommodate another complete episode"
                    )
                directory = Path(config.data_directory) / task["task_id"]
                model = (
                    FixtureModel(
                        [
                            f"<command>{(directory / 'solution/solve.sh').read_text()}</command>",
                            "<action>done</action>",
                        ]
                    )
                    if config.mode == "fixture"
                    else EndpointModel(
                        session.base_url
                        if session is not None
                        else str(config.base_url),
                        config.model_name,
                        config.max_tokens,
                        config.temperature,
                    )
                )
                episode = run_episode(
                    {**task, "dataset_revision": prepared["dataset_revision"]},
                    directory,
                    model,
                    output / task["task_id"],
                    identity=evaluation["model"],
                    max_actions=config.max_actions,
                    command_timeout=config.command_timeout,
                    episode_timeout=config.episode_timeout,
                )
                evaluation["episodes"].append(episode)
                (output / "evaluation.json").write_text(
                    json.dumps(evaluation, indent=2)
                )
                summary = summarize_evaluation(evaluation)
                if summary["infrastructure_errors"] or summary["incomplete"]:
                    raise RuntimeError(
                        f"Episode infrastructure failed: {task['task_id']}"
                    )
                if config.mode == "fixture" and summary["failures"]:
                    raise RuntimeError("Reference fixture failed its task")
        evaluation["status"] = "completed"
    except BaseException as exc:
        error = exc
        evaluation["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        evaluation["cleanup"] = (
            session.cleanup_report
            if session is not None
            else {
                "complete": all(
                    e.get("cleanup_complete") is True
                    for e in evaluation["episodes"]
                ),
                "inference": "externally managed"
                if config.mode == "endpoint"
                else "not allocated",
            }
        )
        evaluation["cleanup"] = dict(evaluation["cleanup"])
        evaluation["cleanup"]["sandboxes_complete"] = all(
            e.get("cleanup_complete") is True for e in evaluation["episodes"]
        )
        evaluation["cleanup"]["complete"] = (
            evaluation["cleanup"]["complete"]
            and evaluation["cleanup"]["sandboxes_complete"]
        )
        if not evaluation["cleanup"]["complete"]:
            evaluation["status"] = "failed"
        (output / "evaluation.json").write_text(
            json.dumps(evaluation, indent=2)
        )
        (output / "report.html").write_text(
            str(render_evaluation_report(evaluation))
        )
    if error is not None or evaluation["status"] != "completed":
        try:
            save_artifact(evaluation, name="failed_evaluation_results")
            save_artifact(
                render_evaluation_report(evaluation),
                name="failed_evaluation_report",
            )
        except Exception as upload_error:
            print(
                f"Partial artifact upload failed: {type(upload_error).__name__}; evidence: {output}"
            )
        if error is not None:
            raise error
        raise RuntimeError(f"Cleanup incomplete; inspect {output}")
    return evaluation


@step(enable_cache=False)
def evaluate_checkpoint(
    prepared: dict[str, Any], config: EvaluationConfig
) -> Annotated[dict[str, Any], "evaluation_results"]:
    """Allocate inference, run episodes, and finish cleanup in this step.

    Args:
        prepared: Qualified task artifact from the preceding step.
        config: Evaluation settings.

    Returns:
        Complete evaluation with inline transcripts and cleanup evidence.
    """
    result = execute_evaluation(
        prepared, config, str(get_step_context().pipeline_run.id)
    )
    log_metadata(metadata=summarize_evaluation(result))
    return result


@step(enable_cache=False)
def report_evaluation(
    evaluation: dict[str, Any], baseline: Optional[dict[str, Any]] = None
) -> tuple[
    Annotated[dict[str, Any], "evaluation_summary"],
    Annotated[HTMLString, "evaluation_report"],
]:
    """Publish deterministic metrics and a dashboard HTML visualization.

    Args:
        evaluation: Current checkpoint results.
        baseline: Optional compatible earlier evaluation artifact.

    Returns:
        Summary metrics and a self-contained HTML report.
    """
    return summarize_evaluation(evaluation), render_evaluation_report(
        evaluation, baseline
    )


@pipeline(enable_cache=False)
def endless_terminals_evaluation(config: EvaluationConfig) -> None:
    """Execute the full evaluation workflow with artifact dependencies.

    Args:
        config: Task selection and bounded inference configuration.
    """
    prepared = prepare_evaluation(config)
    evaluation = evaluate_checkpoint(prepared, config)
    if config.baseline_artifact_id:
        report_evaluation(
            evaluation,
            baseline=ExternalArtifact(id=config.baseline_artifact_id),
        )
    else:
        report_evaluation(evaluation)
