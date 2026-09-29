"""Run bounded, task-reward-only RL with matched before/after evaluations."""

import hashlib
import json
import time
from pathlib import Path
from types import TracebackType
from typing import Annotated, Any, Callable, Protocol

from cloud import KubernetesInference
from config import TrainingConfig
from dataset import sha256
from pipeline import prepare_evaluation
from reporting import render_evaluation_report, summarize_evaluation
from runtime.contract import CONCISE_XML_V1_SYSTEM_MESSAGE, SYSTEM_MESSAGE
from runtime.environment import TerminalEnvironment
from runtime.runner import run_episode
from training_client import TinkerPolicy

from zenml import (
    ArtifactConfig,
    get_step_context,
    log_metadata,
    pipeline,
    save_artifact,
    step,
)
from zenml.enums import ArtifactType
from zenml.types import HTMLString

EnvironmentFactory = Callable[[str, float, float], TerminalEnvironment]


class TrainingService(Protocol):
    """Bound the service contract shared by local and in-cluster training."""

    identity: dict[str, Any]
    base_url: str
    cleanup_report: dict[str, Any]

    @property
    def serving_seconds_remaining(self) -> float:
        """Return the remaining hard service lifetime.

        Returns:
            Seconds remaining before the service deadline.
        """
        ...

    def __enter__(self) -> "TrainingService":
        """Start the service and wait for readiness.

        Returns:
            Ready training service.
        """
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Release service resources after success or failure.

        Args:
            exc_type: Raised exception class, if any.
            exc_value: Raised exception instance, if any.
            traceback: Exception traceback, if any.

        Returns:
            Whether the exception should be suppressed.
        """
        ...


def evaluate_policy(
    policy: TinkerPolicy,
    snapshot: dict[str, Any],
    prepared: dict[str, Any],
    config: TrainingConfig,
    directory: Path,
    session: TrainingService,
    protocol: dict[str, Any],
    *,
    system_message: str = SYSTEM_MESSAGE,
    data_directory: Path | None = None,
    environment_factory: EnvironmentFactory | None = None,
) -> dict[str, Any]:
    """Evaluate one immutable snapshot under the shared comparison protocol.

    Args:
        policy: Connected training policy.
        snapshot: Fixed sampling checkpoint.
        prepared: CPU-qualified tasks.
        config: Evaluation limits.
        directory: New episode output directory.
        session: Bounded GPU service.
        protocol: Identical configuration for both evaluations.
        system_message: Selected system prompt shared by all training phases.
        data_directory: Materialized task bundle, or the legacy configured directory.
        environment_factory: Constructor for isolated terminal environments.

    Returns:
        Evaluation evidence compatible with the existing report renderer.

    Raises:
        RuntimeError: The service budget or episode infrastructure fails.
    """
    result = {
        "run_id": directory.name,
        "mode": "model",
        "model": {
            "name": config.model_name,
            "revision": config.model_revision,
            "revision_verified": True,
            "checkpoint": snapshot["identity"],
        },
        "dataset_revision": prepared["dataset_revision"],
        "protocol": protocol,
        "task_hashes": {
            t["task_id"]: {
                "files": t["task_file_sha256"],
                "image": t.get("image_ref") or t["local_image_id"],
            }
            for t in prepared["tasks"]
        },
        "episodes": [],
        "status": "running",
        "cleanup": {"complete": False},
    }
    directory.mkdir(parents=True, exist_ok=False)
    for task in prepared["tasks"]:
        for attempt_index in range(1, config.evaluation_attempts + 1):
            episode_directory = directory / task["task_id"]
            if config.evaluation_attempts > 1:
                episode_directory /= f"attempt-{attempt_index:02d}"
            if (
                session.serving_seconds_remaining
                < config.episode_timeout + 300
            ):
                raise RuntimeError(
                    "Insufficient service lifetime for evaluation"
                )
            episode = run_episode(
                {**task, "dataset_revision": prepared["dataset_revision"]},
                (data_directory or Path(config.data_directory))
                / task["task_id"],
                policy.episode_model(snapshot),
                episode_directory,
                identity=result["model"],
                system_message=system_message,
                max_actions=config.max_actions,
                command_timeout=config.command_timeout,
                episode_timeout=config.episode_timeout,
                environment_factory=environment_factory,
            )
            episode["attempt_index"] = attempt_index
            result["episodes"].append(episode)
            (directory / "evaluation.json").write_text(
                json.dumps(result, indent=2)
            )
            summary = summarize_evaluation(result)
            if summary["infrastructure_errors"] or summary["incomplete"]:
                raise RuntimeError(
                    "Evaluation infrastructure failed; inspect episode evidence"
                )
    result["status"] = "completed"
    return result


def execute_training(
    prepared: dict[str, Any],
    config: TrainingConfig,
    run_id: str,
    *,
    session: TrainingService | None = None,
    environment_factory: EnvironmentFactory | None = None,
    data_directory: Path | None = None,
    output_directory: Path | None = None,
    client_api_key: str = "tml-local-skyrl",
    trusted_service_host: str | None = None,
    client_credentials_factory: Callable[[], tuple[str, str]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    """Allocate one GPU service for evaluation, updates, and checkpoint export.

    Args:
        prepared: Qualified task evidence.
        config: Explicit bounded training settings.
        run_id: Native ZenML pipeline run ID.
        session: Injected service, or a legacy Kubernetes inference session.
        environment_factory: Constructor for isolated terminal environments.
        data_directory: Materialized task bundle directory.
        output_directory: Run output directory retained through materialization.
        client_api_key: Authentication for the training service.
        trusted_service_host: Exact cluster DNS name trusted for adapter downloads.
        client_credentials_factory: Resolve authentication and the exact owned
            host after the service starts, when its endpoint is assigned.

    Returns:
        Before evaluation, after evaluation, training evidence, and adapter directory.

    Raises:
        ValueError: Training tasks are absent from the qualified selection.
        RuntimeError: Episodes, training, checkpoint export, or cleanup fail.
    """  # noqa: DOC503
    system_message = {
        "upstream": SYSTEM_MESSAGE,
        "concise_xml_v1": CONCISE_XML_V1_SYSTEM_MESSAGE,
    }[config.prompt_variant]
    tasks = {task["task_id"]: task for task in prepared["tasks"]}
    if (
        not config.training_task_ids
        or not set(config.training_task_ids) <= tasks.keys()
    ):
        raise ValueError(
            "All training tasks must be in the qualified evaluation selection"
        )
    output = output_directory or Path(config.output_directory) / run_id
    output.mkdir(parents=True, exist_ok=False)
    if session is None:
        cloud = json.loads(Path(str(config.cloud_config_path)).read_text())
        cloud["server_kind"] = "skyrl"
        session = KubernetesInference(
            cloud,
            {"name": config.model_name, "revision": config.model_revision},
            run_id,
            output / "service",
        )
        training_image = cloud["training_image"]
    else:
        training_image = session.identity["training_image"]
    evidence: dict[str, Any] = {
        "run_id": run_id,
        "scope": "Training-set demonstration; no held-out claim",
        "reward": "1 for audited task pass, 0 for audited task failure; no auxiliary rewards",
        "config": config.model_dump(mode="json"),
        "service": session.identity,
        "groups": [],
        "optimizer_steps": 0,
        "status": "failed",
        "stop_reason": "not_started",
    }
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    checkpoint = output / "checkpoint"
    protocol = {
        "backend": "skyrl_tinker",
        "prompt_variant": config.prompt_variant,
        "system_prompt_sha256": hashlib.sha256(
            system_message.encode()
        ).hexdigest(),
        "evaluation_attempts": config.evaluation_attempts,
        "max_actions": config.max_actions,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "max_context": config.max_context,
        "episode_timeout": config.episode_timeout,
        "command_timeout": config.command_timeout,
        "training_image": training_image,
        "source_sha256": {
            str(p.relative_to(Path(__file__).parent)): sha256(p)
            for p in sorted(Path(__file__).parent.rglob("*.py"))
            if "tests" not in p.parts
        },
    }
    evidence["protocol"] = protocol
    try:
        with session:
            if client_credentials_factory is not None:
                client_api_key, trusted_service_host = (
                    client_credentials_factory()
                )
            policy = TinkerPolicy(
                session.base_url,
                config.model_name,
                config.model_revision,
                rank=config.lora_rank,
                learning_rate=config.learning_rate,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                max_context=config.max_context,
                api_key=client_api_key,
                trusted_service_host=trusted_service_host,
            )
            # The first sampler save also initializes the cold inference engine.
            initial_sampler_timeout = min(
                600.0, session.serving_seconds_remaining
            )
            evidence["initial_sampler_timeout_seconds"] = (
                initial_sampler_timeout
            )
            snapshot = policy.snapshot(
                "before", timeout=initial_sampler_timeout
            )
            evaluation_started = time.monotonic()
            before = evaluate_policy(
                policy,
                snapshot,
                prepared,
                config,
                output / "before",
                session,
                protocol,
                system_message=system_message,
                data_directory=data_directory,
                environment_factory=environment_factory,
            )
            evaluation_seconds = time.monotonic() - evaluation_started
            initial_manifest = policy.download_checkpoint(
                "initial", output / "initial_checkpoint"
            )
            evidence["initial_checkpoint"] = json.loads(
                initial_manifest.read_text()
            )
            (output / "training.json").write_text(
                json.dumps(evidence, indent=2)
            )
            no_signal = 0
            evidence["stop_reason"] = "group_limit"
            for index in range(config.groups):
                # Reserve time for the complete paired evaluation and adapter export.
                reserve = (
                    max(
                        evaluation_seconds * 2,
                        config.evaluation_attempts
                        * len(tasks)
                        * config.episode_timeout
                        + evaluation_seconds,
                        config.episode_timeout + 420,
                    )
                    + 660
                )
                evidence["paired_evaluation_reserve_seconds"] = reserve
                evidence["reserve_basis"] = (
                    "heuristic: maximum of twice observed evaluation time, all paired interaction budgets plus observed evaluation time, and single-episode margin; plus 660s sampler save, client creation, and export; infrastructure stalls may exhaust the hard service lifetime"
                )
                if (
                    session.serving_seconds_remaining
                    < reserve
                    + config.group_size * (config.episode_timeout + 150)
                    + 480
                ):
                    evidence["stop_reason"] = "service_budget"
                    break
                task_id = config.training_task_ids[
                    index % len(config.training_task_ids)
                ]
                group: dict[str, Any] = {
                    "index": index,
                    "task_id": task_id,
                    "checkpoint": snapshot["identity"],
                    "episodes": [],
                    "rewards": [],
                }
                samples = []
                evidence["groups"].append(group)
                for sample_index in range(config.group_size):
                    model = policy.episode_model(snapshot)
                    episode = run_episode(
                        {
                            **tasks[task_id],
                            "dataset_revision": prepared["dataset_revision"],
                        },
                        (data_directory or Path(config.data_directory))
                        / task_id,
                        model,
                        output
                        / "training"
                        / f"group-{index:02d}"
                        / f"sample-{sample_index:02d}",
                        identity=snapshot["identity"],
                        system_message=system_message,
                        max_actions=config.training_max_actions,
                        command_timeout=config.command_timeout,
                        episode_timeout=config.episode_timeout,
                        environment_factory=environment_factory,
                    )
                    group["episodes"].append(episode)
                    summary = summarize_evaluation({"episodes": [episode]})
                    if (
                        summary["infrastructure_errors"]
                        or summary["incomplete"]
                    ):
                        raise RuntimeError(
                            "Training episode infrastructure failed"
                        )
                    group["rewards"].append(float(summary["passes"]))
                    samples.append(model.samples)
                    (output / "training.json").write_text(
                        json.dumps(evidence, indent=2)
                    )
                group["samples"] = samples
                (output / "training.json").write_text(
                    json.dumps(evidence, indent=2)
                )
                group["update"] = policy.update(samples, group["rewards"])
                evidence["optimizer_steps"] = policy.optimizer_steps
                no_signal = 0 if group["update"]["updated"] else no_signal + 1
                if group["update"]["updated"]:
                    snapshot = policy.snapshot(
                        f"update-{policy.optimizer_steps:02d}"
                    )
                if no_signal >= config.zero_signal_patience:
                    evidence["stop_reason"] = "no_reward_variation"
                    break
            after = evaluate_policy(
                policy,
                snapshot,
                prepared,
                config,
                output / "after",
                session,
                protocol,
                system_message=system_message,
                data_directory=data_directory,
                environment_factory=environment_factory,
            )
            checkpoint_manifest = policy.download_checkpoint(
                "final", checkpoint
            )
            evidence["checkpoint"] = json.loads(
                checkpoint_manifest.read_text()
            )
            evidence["status"] = "completed"
    except BaseException as exc:
        evidence["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        evidence["cleanup"] = session.cleanup_report
        if not session.cleanup_report["complete"]:
            evidence["status"] = "failed"
        for name, evaluation in (("before", before), ("after", after)):
            evaluation_path = output / name / "evaluation.json"
            if not evaluation and evaluation_path.is_file():
                evaluation = json.loads(evaluation_path.read_text())
                evaluation["status"] = "failed"
                if "error" in evidence:
                    evaluation["error"] = evidence["error"]
            if evaluation:
                evaluation["cleanup"] = session.cleanup_report
                evaluation_path.write_text(json.dumps(evaluation, indent=2))
        (output / "training.json").write_text(json.dumps(evidence, indent=2))
        if evidence["status"] != "completed":
            try:
                save_artifact(evidence, name="failed_training_evidence")
                save_artifact(output, name="failed_training_diagnostics")
            except Exception:
                print(f"Partial training evidence retained at {output}")
    if evidence["status"] != "completed":
        raise RuntimeError("Training or cleanup did not complete")
    return before, after, evidence, checkpoint


@step(enable_cache=False)
def train_and_evaluate(
    prepared: dict[str, Any], config: TrainingConfig
) -> tuple[
    Annotated[dict[str, Any], "before_evaluation"],
    Annotated[dict[str, Any], "after_evaluation"],
    Annotated[dict[str, Any], "training_evidence"],
    Annotated[
        Path,
        ArtifactConfig(
            name="trained_adapter", artifact_type=ArtifactType.MODEL
        ),
    ],
]:
    """Train and export a sampler adapter within one owned GPU session.

    Args:
        prepared: CPU-qualified tasks.
        config: Bounded training settings.

    Returns:
        Paired evaluations, training evidence, and durable sampler adapter.
    """
    before, after, evidence, checkpoint = execute_training(
        prepared, config, str(get_step_context().pipeline_run.id)
    )
    log_metadata(
        metadata={
            "optimizer_steps": evidence["optimizer_steps"],
            "stop_reason": evidence["stop_reason"],
        }
    )
    return before, after, evidence, checkpoint


@step(enable_cache=False)
def report_training(
    before: dict[str, Any],
    after_evaluation: dict[str, Any],
    training: dict[str, Any],
) -> Annotated[HTMLString, "training_report"]:
    """Publish paired task results with explicit training limitations.

    Args:
        before: Fresh evaluation before updates.
        after_evaluation: Matched evaluation after updates.
        training: Recorded update and cleanup evidence.

    Returns:
        Self-contained HTML report for the ZenML dashboard.
    """
    import html

    report = str(render_evaluation_report(after_evaluation, before))
    details = "<section><h2>Training-set pilot</h2><p>No held-out generalization claim. "
    details += f"Optimizer steps: {training['optimizer_steps']}. Stop reason: {html.escape(training['stop_reason'])}. "
    details += "Checkpoint contains sampling adapter weights, not resumable optimizer state.</p>"
    summary = {
        **training,
        "groups": [
            {
                key: value
                for key, value in group.items()
                if key not in {"samples", "episodes"}
            }
            for group in training["groups"]
        ],
    }
    details += (
        "<p>Exact sampled tokens and full training episodes are retained in the "
        "training_evidence artifact.</p>"
        "<details><summary>Training rewards and updates</summary><pre>"
        + html.escape(json.dumps(summary, indent=2))
        + "</pre></details></section>"
    )
    return HTMLString(report.replace("</body>", details + "</body>"))


@pipeline(enable_cache=False)
def endless_terminals_training(config: TrainingConfig) -> None:
    """Qualify, train, evaluate, export, and report through native artifacts.

    Args:
        config: Explicit task and compute settings.
    """
    prepared = prepare_evaluation(config)
    before, after, training, checkpoint = train_and_evaluate(prepared, config)
    report_training(before, after, training)
