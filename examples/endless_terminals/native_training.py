"""Qualify portable tasks before starting a bounded native GPU training service."""

import tempfile
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from config import TrainingConfig
from modal_service import ModalServiceConfig, ModalTrainingService
from native_service import NativeServiceConfig, NativeTrainingService
from pydantic import BaseModel, Field, model_validator
from sandbox_pipeline import (
    SandboxPipelineConfig,
    create_environment,
    evaluate_sandbox_fixture,
    fixture_matches,
    load_bundle_task,
    qualify_sandbox_initial,
    report_sandbox_results,
)
from training import execute_training, report_training

from zenml import (
    ArtifactConfig,
    get_step_context,
    pipeline,
    save_artifact,
    step,
)
from zenml.client import Client
from zenml.enums import ArtifactType

PILOT_TASK = "task_000000_0228cd64"


class NativeTrainingConfig(BaseModel):
    """Combine portable training limits with CPU and GPU runtime settings."""

    controller_image: str = Field(pattern=r"^[^\s@]+@sha256:[0-9a-f]{64}$")
    training: TrainingConfig
    sandbox: SandboxPipelineConfig
    service: NativeServiceConfig | ModalServiceConfig

    @model_validator(mode="after")
    def validate_pilot(self) -> "NativeTrainingConfig":
        """Require the canonical single-task pilot and injected native service.

        Returns:
            Validated native configuration.

        Raises:
            ValueError: Configuration expands the pilot or uses local cloud paths.
        """
        if isinstance(self.service, ModalServiceConfig) and (
            self.sandbox.modal_workspace != self.service.workspace
            or self.sandbox.modal_environment != self.service.modal_environment
        ):
            raise ValueError(
                "Sandbox and service Modal workspace/environment must match"
            )
        if self.training.mode != "native" or self.training.cloud_config_path:
            raise ValueError(
                "Native training requires mode=native and no cloud config"
            )
        if any(
            selection != [PILOT_TASK]
            for selection in (
                self.training.task_ids,
                self.training.training_task_ids,
                self.sandbox.task_ids,
            )
        ):
            raise ValueError("The native pilot must select only " + PILOT_TASK)
        return self


@step(enable_cache=False)
def train_native(
    bundle: Path,
    initial: dict[str, Any],
    reference: dict[str, Any],
    noop: dict[str, Any],
    config: NativeTrainingConfig,
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
    """Start training only after initial, reference, and no-op qualification passes.

    Args:
        bundle: Materialized, immutable task bundle.
        initial: Initial grading and cleanup evidence.
        reference: Known-solution episode evidence.
        noop: Known-failure episode evidence.
        config: Validated pilot runtime and training limits.

    Returns:
        Matched evaluations, training evidence, and persistent checkpoint directory.

    Raises:
        RuntimeError: Qualification, training, export, or cleanup fails.
    """
    task = load_bundle_task(bundle, config.sandbox)
    grading = initial.get("grading") or {}
    if (
        initial.get("task") != task
        or not initial.get("cleanup_complete")
        or not grading.get("audited_valid")
        or grading.get("infrastructure_error")
        or not fixture_matches(reference, 1)
        or not fixture_matches(noop, 0)
    ):
        save_artifact(
            {"initial": initial, "reference": reference, "noop": noop},
            name="failed_native_qualification",
        )
        raise RuntimeError(
            "CPU qualification failed; GPU service was not started"
        )
    run_id = str(get_step_context().pipeline_run.id)
    # ZenML materializes Path outputs after this function returns.
    directory = (
        Path(tempfile.mkdtemp(prefix="endless-native-training-")) / run_id
    )
    model = {
        "name": config.training.model_name,
        "revision": config.training.model_revision,
    }
    session: NativeTrainingService | ModalTrainingService
    if isinstance(config.service, ModalServiceConfig):
        session = ModalTrainingService(
            config.service, model, run_id, directory / "service"
        )
    else:
        session = NativeTrainingService(
            config.service, model, run_id, directory / "service"
        )
    before, after, evidence, checkpoint = execute_training(
        {"dataset_revision": task["dataset_revision"], "tasks": [task]},
        config.training,
        run_id,
        session=session,
        data_directory=bundle,
        output_directory=directory,
        environment_factory=lambda image, command, episode: create_environment(
            {**task, "image_ref": image},
            config.sandbox.model_copy(
                update={"command_timeout": command, "episode_timeout": episode}
            ),
        ),
        client_credentials_factory=lambda: (
            session.api_key,
            session.service_host,
        ),
    )
    save_artifact(directory / "service", name="native_training_diagnostics")
    save_artifact(directory / "initial_checkpoint", name="initial_adapter")

    return before, after, evidence, checkpoint


@pipeline(enable_cache=False)
def endless_terminals_native_training(
    bundle_artifact_id: UUID, config: NativeTrainingConfig
) -> None:
    """Link CPU qualification artifacts to native training and paired reporting.

    Args:
        bundle_artifact_id: Version ID of the uploaded portable task directory.
        config: Validated pilot runtime and training limits.
    """
    bundle = Client().get_artifact_version(bundle_artifact_id)
    initial = qualify_sandbox_initial(bundle, config.sandbox)
    reference = evaluate_sandbox_fixture(
        bundle, initial, config.sandbox, "reference", id="reference_fixture"
    )
    noop = evaluate_sandbox_fixture(
        bundle, initial, config.sandbox, "noop", id="noop_fixture"
    )
    report_sandbox_results(initial, reference, noop)
    before, after, evidence, checkpoint = train_native(
        bundle, initial, reference, noop, config
    )
    report_training(before, after, evidence)
