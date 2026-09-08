"""Screen qualified tasks with one unchanged sampler and a fixed GPU budget."""

import hashlib
import html
import json
import tempfile
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from dataset import sha256
from modal_service import ModalServiceConfig, ModalTrainingService
from pydantic import BaseModel, ConfigDict, Field, model_validator
from reporting import render_evaluation_report, summarize_evaluation
from runtime.contract import CONCISE_XML_V1_SYSTEM_MESSAGE, SYSTEM_MESSAGE
from runtime.runner import run_episode
from sandbox_pipeline import (
    SandboxPipelineConfig,
    create_environment,
    evaluate_sandbox_fixture,
    fixture_matches,
    load_bundle_task,
    qualify_sandbox_initial,
)
from training_client import TinkerPolicy

from zenml import get_step_context, pipeline, save_artifact, step
from zenml.client import Client
from zenml.types import HTMLString


class BaselineConfig(BaseModel):
    """Pin the screening model, task selection, and bounded Modal resources."""

    model_config = ConfigDict(extra="forbid")
    controller_image: str = Field(pattern=r"^[^\s@]+@sha256:[0-9a-f]{64}$")
    model_name: Literal["Qwen/Qwen2.5-7B-Instruct"] = (
        "Qwen/Qwen2.5-7B-Instruct"
    )
    model_revision: Literal["a09a35458c702b33eeacc393d103063234e8bc28"] = (
        "a09a35458c702b33eeacc393d103063234e8bc28"
    )
    task_ids: list[str] = Field(min_length=1, max_length=20)
    sandbox: SandboxPipelineConfig
    service: ModalServiceConfig
    modal_agent_images: dict[str, str] = Field(default_factory=dict)
    attempts_per_task: Literal[3] = 3
    prompt_variant: Literal["upstream", "concise_xml_v1"] = "concise_xml_v1"
    temperature: float = Field(default=0.8, ge=0.8, le=0.8)
    max_tokens: Literal[512] = 512
    max_actions: Literal[8] = 8
    episode_timeout: Literal[90] = 90
    command_timeout: float = Field(default=10, gt=0, le=90)
    max_context: Literal[8192] = 8192

    @model_validator(mode="after")
    def validate_selection(self) -> "BaselineConfig":
        """Reject ambiguous selections and invalid task image overrides.

        Returns:
            Validated baseline configuration.

        Raises:
            ValueError: IDs are duplicated or image overrides are invalid.
        """
        if (
            self.sandbox.modal_workspace != self.service.workspace
            or self.sandbox.modal_environment != self.service.modal_environment
        ):
            raise ValueError(
                "Sandbox and service Modal workspace/environment must match"
            )
        if len(set(self.task_ids)) != len(self.task_ids):
            raise ValueError("Task IDs must be unique")
        if set(self.modal_agent_images) != set(self.task_ids):
            raise ValueError(
                "Every selected task requires its own Modal agent image"
            )
        for task_id in self.task_ids:
            self.task_config(task_id)
        return self

    def task_config(self, task_id: str) -> SandboxPipelineConfig:
        """Build validated runtime settings for exactly one selected task.

        Args:
            task_id: Selected task identifier.

        Returns:
            Single-task sandbox settings with the correct Modal image.
        """
        values = self.sandbox.model_dump()
        values.update(
            task_ids=[task_id],
            episode_timeout=self.episode_timeout,
            command_timeout=self.command_timeout,
        )
        if task_id in self.modal_agent_images:
            values["modal_agent_image"] = self.modal_agent_images[task_id]
        return SandboxPipelineConfig.model_validate(values)


@step(enable_cache=False, settings={"orchestrator": {"timeout": 3600}})
def qualify_baseline_tasks(
    bundle: Path, config: BaselineConfig
) -> Annotated[dict[str, Any], "baseline_qualification"]:
    """Run all three CPU checks for each task before any GPU allocation.

    Args:
        bundle: Immutable uploaded task bundle.
        config: Task selection and sandbox settings.

    Returns:
        Per-task checks and explicit qualified and rejected selections.
    """
    result: dict[str, Any] = {"tasks": [], "qualified": [], "rejected": []}
    for task_id in config.task_ids:
        settings = config.task_config(task_id)
        task = load_bundle_task(bundle, settings)
        initial = qualify_sandbox_initial.entrypoint(bundle, settings)
        reference = evaluate_sandbox_fixture.entrypoint(
            bundle, initial, settings, "reference"
        )
        noop = evaluate_sandbox_fixture.entrypoint(
            bundle, initial, settings, "noop"
        )
        grade = initial.get("grading") or {}
        valid = (
            initial.get("task") == task
            and initial.get("cleanup_complete") is True
            and grade.get("audited_valid") is True
            and not grade.get("infrastructure_error")
            and fixture_matches(reference, 1)
            and fixture_matches(noop, 0)
        )
        result["tasks"].append(
            {
                "task": task,
                "initial": initial,
                "reference": reference,
                "noop": noop,
                "qualified": bool(valid),
                "rejection_reason": None
                if valid
                else "initial, reference, noop, or cleanup check failed",
            }
        )
        result["qualified" if valid else "rejected"].append(task_id)
        save_artifact(result, name="baseline_qualification_progress")
    return result


def baseline_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Separate graded task outcomes from invalid and unattempted episodes.

    Args:
        result: Baseline evidence, including its intended task selection.

    Returns:
        Aggregate counts and per-task attempt outcomes.
    """
    summary = summarize_evaluation(result)
    summary["tasks"] = {}
    for task_id in result["selected_task_ids"]:
        episodes = [e for e in result["episodes"] if e["task_id"] == task_id]
        counts = summarize_evaluation({"episodes": episodes})
        summary["tasks"][task_id] = {
            key: counts[key]
            for key in (
                "attempts",
                "passes",
                "failures",
                "infrastructure_errors",
                "incomplete",
            )
        }
        summary["tasks"][task_id]["unattempted"] = result[
            "attempts_per_task"
        ] - len(episodes)
    summary["status"] = result["status"]
    summary["unattempted"] = len(result["unattempted"])
    return summary


def render_baseline_report(result: dict[str, Any]) -> HTMLString:
    """Show attempt coverage and per-task screening outcomes with transcripts.

    Args:
        result: Complete or bounded baseline evidence.

    Returns:
        Self-contained baseline screening report.
    """
    summary = baseline_summary(result)
    rows = "".join(
        "<tr><td>"
        + html.escape(task_id)
        + "</td>"
        + "".join(
            f"<td>{counts[key]}</td>"
            for key in (
                "passes",
                "failures",
                "infrastructure_errors",
                "incomplete",
                "unattempted",
            )
        )
        + "</tr>"
        for task_id, counts in summary["tasks"].items()
    )
    coverage = (
        "<h2>Unchanged-model screening</h2>"
        "<p>Optimizer updates: 0. Three planned attempts per qualified task. "
        "Infrastructure-invalid and unattempted episodes are not task failures.</p>"
        "<table><tr><th>Task</th><th>Passes</th><th>Failures</th>"
        "<th>Infrastructure errors</th><th>Incomplete</th><th>Unattempted</th></tr>"
        + rows
        + "</table><details><summary>CPU qualification and rejected tasks</summary><pre>"
        + html.escape(json.dumps(result["qualification"], indent=2))
        + "</pre></details>"
    )
    display = {
        **result,
        "episodes": [
            {
                **episode,
                "task_id": f"{episode['task_id']} / attempt {episode['attempt_index']}",
            }
            for episode in result["episodes"]
        ],
    }
    report = str(render_evaluation_report(display))
    return HTMLString(
        report.replace(
            "<h2>Task results</h2>", coverage + "<h2>Task results</h2>"
        )
    )


def execute_baseline(
    bundle: Path,
    qualification: dict[str, Any],
    config: BaselineConfig,
    run_id: str,
    output: Path,
) -> dict[str, Any]:
    """Evaluate one zero-update snapshot and retain evidence through failures.

    Args:
        bundle: Materialized task directory.
        qualification: Completed CPU check evidence for every selected task.
        config: Pinned baseline limits and resources.
        run_id: Unique pipeline run identifier.
        output: New persistent local evidence directory.

    Returns:
        Completed or budget-limited baseline evidence.

    Raises:
        RuntimeError: Qualification, provider execution, or cleanup is invalid.
    """  # noqa: DOC503
    entries = qualification.get("tasks", [])
    if [entry["task"]["task_id"] for entry in entries] != config.task_ids:
        raise RuntimeError(
            "CPU qualification missing tasks; GPU service was not started"
        )
    accepted = []
    for entry in entries:
        task = entry["task"]
        if (
            load_bundle_task(bundle, config.task_config(task["task_id"]))
            != task
        ):
            raise RuntimeError(
                "Qualified task identities changed; GPU service was not started"
            )
        if not all(
            entry[phase].get("cleanup_complete") is True
            for phase in ("initial", "reference", "noop")
        ):
            raise RuntimeError(
                "CPU cleanup failed; GPU service was not started"
            )
        grade = entry["initial"].get("grading") or {}
        valid = (
            entry["initial"].get("task") == task
            and grade.get("audited_valid") is True
            and not grade.get("infrastructure_error")
            and fixture_matches(entry["reference"], 1)
            and fixture_matches(entry["noop"], 0)
        )
        if valid:
            accepted.append(task)
    if not accepted:
        raise RuntimeError("No tasks qualified; GPU service was not started")
    tasks = accepted
    accepted_ids = [task["task_id"] for task in tasks]
    output.mkdir(parents=True, exist_ok=False)
    system_message = (
        CONCISE_XML_V1_SYSTEM_MESSAGE
        if config.prompt_variant == "concise_xml_v1"
        else SYSTEM_MESSAGE
    )
    schedule = [
        {"task_id": task_id, "attempt_index": index}
        for index in range(1, config.attempts_per_task + 1)
        for task_id in accepted_ids
    ]
    result: dict[str, Any] = {
        "run_id": run_id,
        "mode": "model",
        "status": "running",
        "model": {
            "name": config.model_name,
            "revision": config.model_revision,
            "revision_verified": True,
        },
        "dataset_revision": tasks[0]["dataset_revision"],
        "selected_task_ids": accepted_ids,
        "requested_task_ids": config.task_ids,
        "qualification": qualification,
        "attempts_per_task": config.attempts_per_task,
        "optimizer_steps": 0,
        "episodes": [],
        "unattempted": schedule.copy(),
        "cleanup": {"complete": False},
        "task_hashes": {
            task["task_id"]: {
                "files": task["task_file_sha256"],
                "image": task["image_ref"],
            }
            for task in tasks
        },
        "protocol": {
            "backend": "skyrl_tinker",
            "prompt_variant": config.prompt_variant,
            "system_prompt_sha256": hashlib.sha256(
                system_message.encode()
            ).hexdigest(),
            "max_actions": config.max_actions,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "max_context": config.max_context,
            "episode_timeout": config.episode_timeout,
            "command_timeout": config.command_timeout,
            "serving_deadline": config.service.serving_deadline,
            "training_image": config.service.training_image,
            "source_sha256": {
                str(path.relative_to(Path(__file__).parent)): sha256(path)
                for path in sorted(Path(__file__).parent.rglob("*.py"))
                if "tests" not in path.parts
            },
        },
    }
    session = ModalTrainingService(
        config.service, result["model"], run_id, output / "service"
    )
    error: BaseException | None = None
    in_flight: dict[str, Any] | None = None
    try:
        with session:
            policy = TinkerPolicy(
                session.base_url,
                config.model_name,
                config.model_revision,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                max_context=config.max_context,
                api_key=session.api_key,
                trusted_service_host=session.service_host,
            )
            snapshot = policy.snapshot(
                "baseline", timeout=min(600, session.serving_seconds_remaining)
            )
            if (
                policy.optimizer_steps != 0
                or snapshot["identity"]["optimizer_steps"] != 0
            ):
                raise RuntimeError(
                    "Baseline sampler must have zero optimizer updates"
                )
            result["model"]["checkpoint"] = snapshot["identity"]
            result["inference"] = session.identity
            (output / "evaluation.json").write_text(
                json.dumps(result, indent=2)
            )
            by_id = {task["task_id"]: task for task in tasks}
            for attempt in schedule:
                if (
                    session.serving_seconds_remaining
                    < config.episode_timeout + 300
                ):
                    result["status"] = "bounded_partial"
                    result["stop_reason"] = "serving_deadline_reserve"
                    break
                task = by_id[attempt["task_id"]]
                settings = config.task_config(task["task_id"])
                in_flight = attempt
                episode = run_episode(
                    task,
                    bundle / task["task_id"],
                    policy.episode_model(snapshot),
                    output
                    / task["task_id"]
                    / f"attempt-{attempt['attempt_index']:02d}",
                    identity=result["model"],
                    system_message=system_message,
                    max_actions=config.max_actions,
                    command_timeout=config.command_timeout,
                    episode_timeout=config.episode_timeout,
                    environment_factory=lambda image, command, duration: (
                        create_environment(
                            {**task, "image_ref": image},
                            settings.model_copy(
                                update={
                                    "command_timeout": command,
                                    "episode_timeout": duration,
                                }
                            ),
                        )
                    ),
                )
                episode["attempt_index"] = attempt["attempt_index"]
                result["episodes"].append(episode)
                in_flight = None
                result["unattempted"].pop(0)
                (output / "evaluation.json").write_text(
                    json.dumps(result, indent=2)
                )
                save_artifact(result, name="baseline_progress")
                if episode.get("cleanup_complete") is not True:
                    raise RuntimeError(
                        "Episode cleanup incomplete; baseline stopped"
                    )
            else:
                result["status"] = "completed"
                result["stop_reason"] = "all_attempts_recorded"
            if policy.optimizer_steps != 0:
                raise RuntimeError("Baseline policy unexpectedly changed")
    except BaseException as exc:
        error = exc
        result["status"] = "failed"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        result["cleanup"] = dict(session.cleanup_report)
        result["cleanup"]["interrupted_attempt"] = in_flight
        result["cleanup"]["sandboxes_complete"] = in_flight is None and all(
            episode.get("cleanup_complete") is True
            for episode in result["episodes"]
        )
        result["cleanup"]["complete"] = (
            result["cleanup"].get("complete") is True
            and result["cleanup"]["sandboxes_complete"]
        )
        if not result["cleanup"]["complete"]:
            result["status"] = "failed"
        result["summary"] = baseline_summary(result)
        (output / "evaluation.json").write_text(json.dumps(result, indent=2))
        (output / "report.html").write_text(
            str(render_baseline_report(result))
        )
        save_artifact(result, name="baseline_results")
        save_artifact(output, name="baseline_diagnostics")
    if error is not None:
        raise error
    if result["status"] == "failed":
        raise RuntimeError(
            "Baseline cleanup incomplete; inspect retained evidence"
        )
    return result


@step(enable_cache=False, settings={"orchestrator": {"timeout": 6000}})
def evaluate_baseline(
    bundle: Path, qualification: dict[str, Any], config: BaselineConfig
) -> Annotated[dict[str, Any], "baseline_evaluation"]:
    """Allocate the bounded GPU service after CPU qualification finishes.

    Args:
        bundle: Immutable task artifact directory.
        qualification: CPU qualification dependency.
        config: Pinned run configuration.

    Returns:
        Baseline evidence with explicit attempt coverage.
    """
    run_id = str(get_step_context().pipeline_run.id)
    output = Path(tempfile.mkdtemp(prefix="endless-baseline-")) / run_id
    result = execute_baseline(bundle, qualification, config, run_id, output)
    save_artifact(render_baseline_report(result), name="baseline_report")
    return result


@pipeline(enable_cache=False)
def endless_terminals_modal_baseline(
    bundle_artifact_id: UUID, config: BaselineConfig
) -> None:
    """Qualify the complete selection before evaluating the unchanged model.

    Args:
        bundle_artifact_id: Uploaded immutable task bundle artifact version.
        config: Screening configuration.
    """
    bundle = Client().get_artifact_version(bundle_artifact_id)
    qualification = qualify_baseline_tasks(bundle, config)
    evaluate_baseline(bundle, qualification, config)
