"""Run the CPU qualification pilot with native Kubernetes sandbox artifacts."""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field
from qualification_report import render_qualification_report
from runtime.environment import TerminalEnvironment
from runtime.grading import grade_environment
from runtime.models import FixtureModel
from runtime.runner import run_episode, verify_task_files

from zenml import pipeline, step
from zenml.client import Client
from zenml.types import HTMLString


class SandboxPipelineConfig(BaseModel):
    """Bound the single-task CPU sandbox qualification pilot."""

    helper_image: str = Field(pattern=r"^[^\s@]+@sha256:[0-9a-f]{64}$")
    modal_agent_image: str | None = Field(
        default=None, pattern=r"^[^\s@]+@sha256:[0-9a-f]{64}$"
    )
    modal_workspace: str = Field(default="zenml-io", pattern=r"^\S+$")
    modal_environment: str = Field(default="dev", pattern=r"^\S+$")
    storage_class: str = "gp2"
    startup_timeout: int = Field(default=600, gt=0, le=900)
    cleanup_timeout: int = Field(default=120, gt=0, le=300)
    command_timeout: float = Field(default=30, gt=0, le=90)
    episode_timeout: float = Field(default=300, gt=0, le=1200)
    task_ids: list[str] = Field(default_factory=list, max_length=1)


def load_bundle_task(
    bundle: Path, config: SandboxPipelineConfig
) -> dict[str, Any]:
    """Validate the selected task and its immutable registry image.

    Args:
        bundle: Materialized bundle artifact directory.
        config: Task selection.

    Returns:
        Verified task manifest entry, without a machine-specific file path.

    Raises:
        ValueError: Selection, file integrity, or registry image is invalid.
    """
    manifest = json.loads((bundle / "task-manifest.json").read_text())
    if not re.fullmatch(r"[0-9a-f]{40}", manifest["dataset_revision"]):
        raise ValueError("The dataset revision must be a pinned commit")
    tasks = manifest["tasks"]
    selected = [
        t
        for t in tasks
        if not config.task_ids or t["task_id"] in config.task_ids
    ]
    if not selected or (config.task_ids and len(selected) != 1):
        raise ValueError("The bundle must contain exactly the requested task")
    task = dict(selected[0])
    task_id = task["task_id"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", task_id):
        raise ValueError("Task ID must be a single safe directory name")
    image = task.get("image_ref", "")
    if not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", image):
        raise ValueError("Task image_ref must use a registry digest")
    required = {
        "instruction.md",
        "tests/test_final_state.py",
        "environment/test_initial_state.py",
        "solution/solve.sh",
    }
    if not required <= task["task_file_sha256"].keys():
        raise ValueError(
            "The bundle must hash instructions, graders, and reference solution"
        )
    directory = bundle / task_id
    if not directory.resolve().is_relative_to(bundle.resolve()):
        raise ValueError("Task directory escapes the bundle")
    verify_task_files(task, directory)
    task["dataset_revision"] = manifest["dataset_revision"]
    return task


def create_environment(
    task: dict[str, Any], config: SandboxPipelineConfig
) -> TerminalEnvironment:
    """Create the active Kubernetes or Modal environment without starting it.

    Args:
        task: Verified task and registry digest.
        config: Runtime limits and storage configuration.

    Returns:
        The environment used for interaction and trusted grading.
    """
    from runtime.sandbox_env import SandboxEnvironment, SandboxRuntimeConfig

    runtime = SandboxRuntimeConfig(
        helper_image=config.helper_image,
        modal_agent_image=config.modal_agent_image,
        modal_workspace=config.modal_workspace,
        modal_environment=config.modal_environment,
        storage_class=config.storage_class,
        startup_timeout=config.startup_timeout,
        cleanup_timeout=config.cleanup_timeout,
        controller_pod_name=(
            os.environ.get("HOSTNAME")
            if os.environ.get("KUBERNETES_SERVICE_HOST")
            else None
        ),
    )
    return SandboxEnvironment(
        task["image_ref"],
        config=runtime,
        command_timeout=config.command_timeout,
        episode_timeout=config.episode_timeout,
    )


@step(enable_cache=False)
def qualify_sandbox_initial(
    bundle: Path, config: SandboxPipelineConfig
) -> Annotated[dict[str, Any], "sandbox_initial_qualification"]:
    """Verify initial state in an isolated Kubernetes sandbox.

    Args:
        bundle: Uploaded task bundle artifact.
        config: Task selection and runtime limits.

    Returns:
        Initial grading, immutable task identity, and cleanup evidence.
    """
    task = load_bundle_task(bundle, config)
    env = create_environment(task, config)
    result: dict[str, Any] = {
        "task": task,
        "phase": "initial",
        "grading": None,
    }
    try:
        with env:
            result["grading"] = grade_environment(
                env,
                bundle / task["task_id"] / "environment/test_initial_state.py",
                task.get("protected_sources", {}),
            )
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        result["cleanup_complete"] = env.closed
        result["runtime"] = env.provenance
    return result


@step(enable_cache=False)
def evaluate_sandbox_fixture(
    bundle: Path,
    initial: dict[str, Any],
    config: SandboxPipelineConfig,
    fixture: Literal["reference", "noop"],
) -> Annotated[dict[str, Any], "sandbox_fixture_episode"]:
    """Exercise the real agent loop with a known successful or failing fixture.

    Args:
        bundle: Materialized task bundle artifact.
        initial: Initial qualification dependency.
        config: Runtime settings.
        fixture: Scripted reference solution or intentionally unsolved state.

    Returns:
        Complete episode evidence, or an explicit qualification failure.
    """
    task = load_bundle_task(bundle, config)
    grade = initial.get("grading") or {}
    if (
        not initial.get("cleanup_complete")
        or not grade.get("audited_valid")
        or grade.get("infrastructure_error")
    ):
        return {
            "fixture": fixture,
            "skipped": "initial qualification failed",
            "cleanup_complete": True,
        }
    directory = bundle / task["task_id"]
    responses = ["<action>done</action>"]
    if fixture == "reference":
        responses.insert(
            0,
            "<command>"
            + (directory / "solution/solve.sh").read_text()
            + "</command>",
        )
    with tempfile.TemporaryDirectory(
        prefix="endless-sandbox-episode-"
    ) as temporary:
        result = run_episode(
            task,
            directory,
            FixtureModel(responses),
            Path(temporary) / "episode",
            identity={
                "name": fixture,
                "kind": "scripted_fixture",
                "model_calls": 0,
            },
            max_actions=2,
            command_timeout=config.command_timeout,
            episode_timeout=config.episode_timeout,
            environment_factory=lambda image, command, episode: (
                create_environment(
                    {**task, "image_ref": image},
                    config.model_copy(
                        update={
                            "command_timeout": command,
                            "episode_timeout": episode,
                        }
                    ),
                )
            ),
        )
    result["fixture"] = fixture
    result["expected_reward"] = int(fixture == "reference")
    return result


def fixture_matches(result: dict[str, Any], expected: int) -> bool:
    """Check a fixture's intended result and runtime integrity.

    Args:
        result: Recorded episode.
        expected: Expected audited binary reward.

    Returns:
        Whether execution, grading, and cleanup match the fixture contract.
    """
    grade = result.get("grading") or {}
    if (
        result.get("exit_reason") != "done"
        or not result.get("cleanup_complete")
        or grade.get("infrastructure_error")
    ):
        return False
    if grade.get("raw_reward") != expected or grade.get(
        "audited_valid"
    ) != bool(expected):
        return False
    if expected == 0:
        counts = grade.get("test_counts", {})
        return (
            bool(counts.get("failure"))
            and not counts.get("error")
            and not counts.get("skipped")
            and all(
                v.get("unchanged") is True
                for v in grade.get("protected_sources", {}).values()
            )
        )
    return True


@step(enable_cache=False)
def report_sandbox_results(
    initial: dict[str, Any], reference: dict[str, Any], noop: dict[str, Any]
) -> tuple[
    Annotated[dict[str, Any], "sandbox_qualification_results"],
    Annotated[HTMLString, "sandbox_qualification_report"],
]:
    """Publish a truthful CPU qualification report and complete episode evidence.

    Args:
        initial: Initial-state qualification evidence.
        reference: Successful scripted fixture episode.
        noop: Intentionally failing scripted fixture episode.

    Returns:
        Structured evidence and a self-contained HTML report.
    """
    passed = fixture_matches(reference, 1) and fixture_matches(noop, 0)
    results: dict[str, Any] = {
        "status": "passed" if passed else "failed",
        "scope": "CPU Kubernetes sandbox qualification; no model inference or training",
        "initial": initial,
        "reference": reference,
        "noop": noop,
    }
    report = render_qualification_report(
        results, fixture_matches(reference, 1), fixture_matches(noop, 0)
    )
    return results, HTMLString(report)


@pipeline(enable_cache=False)
def endless_terminals_sandbox(
    bundle_artifact_id: UUID, config: SandboxPipelineConfig
) -> None:
    """Run initial qualification and both fixture episodes as artifact-linked steps.

    Args:
        bundle_artifact_id: Version ID of the uploaded task directory artifact.
        config: Single-task CPU runtime settings.
    """
    bundle = Client().get_artifact_version(bundle_artifact_id)
    initial = qualify_sandbox_initial(bundle, config)
    reference = evaluate_sandbox_fixture(
        bundle, initial, config, "reference", id="reference_fixture"
    )
    noop = evaluate_sandbox_fixture(
        bundle, initial, config, "noop", id="noop_fixture"
    )
    report_sandbox_results(initial, reference, noop)
