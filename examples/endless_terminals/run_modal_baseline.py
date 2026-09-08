"""Submit the bounded unchanged-model baseline to the configured Modal workspace."""

import argparse
from pathlib import Path

import modal
from baseline import BaselineConfig, endless_terminals_modal_baseline
from modal_service import ModalServiceConfig
from sandbox_pipeline import load_bundle_task

from zenml import save_artifact
from zenml.client import Client
from zenml.config import DockerSettings, ResourceSettings
from zenml.config.docker_settings import DockerBuildConfig, DockerBuildOptions
from zenml.integrations.modal.flavors import ModalOrchestratorSettings
from zenml.integrations.modal.orchestrators.modal_orchestrator import (
    ModalOrchestrator,
)
from zenml.integrations.modal.sandbox_utils import (
    create_modal_client_from_credentials,
)
from zenml.integrations.modal.sandboxes.modal_sandbox import ModalSandbox


def main() -> None:
    """Validate the active stack and submit the baseline pipeline.

    Raises:
        RuntimeError: The active stack lacks Modal orchestration or sandbox, or identity differs.
        ValueError: The bundle directory is missing.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = BaselineConfig.model_validate_json(args.config.read_text())
    bundle = args.bundle.resolve()
    if not bundle.is_dir() or not (bundle / "task-manifest.json").is_file():
        raise ValueError("--bundle must contain task-manifest.json")
    for task_id in config.task_ids:
        load_bundle_task(bundle, config.task_config(task_id))
    stack = Client().active_stack
    if (
        not isinstance(stack.orchestrator, ModalOrchestrator)
        or stack.sandbox is None
        or not isinstance(stack.sandbox, ModalSandbox)
    ):
        raise RuntimeError(
            "Select a stack with Modal orchestrator and Modal sandbox"
        )
    if not isinstance(config.service, ModalServiceConfig):
        raise ValueError(
            "Modal submission requires a Modal service configuration"
        )
    for component in (stack.orchestrator, stack.sandbox):
        settings = component.config
        if settings.modal_environment != config.service.modal_environment:
            raise RuntimeError(
                f"Both Modal components must select {config.service.modal_environment}"
            )
        if not settings.token_id or not settings.token_secret:
            raise RuntimeError(
                "Both Modal components require explicit credentials"
            )
        client = create_modal_client_from_credentials(
            token_id=settings.token_id, token_secret=settings.token_secret
        )
        workspace = modal.Workspace.from_context(client=client).hydrate()
        if workspace.name != config.service.workspace:
            raise RuntimeError(
                f"Modal credentials do not target {config.service.workspace}"
            )
    print(
        f"Verified Modal workspace={config.service.workspace} "
        f"environment={config.service.modal_environment} for both components"
    )
    configured = endless_terminals_modal_baseline.with_options(
        settings={
            "docker": DockerSettings(
                parent_image=config.controller_image,
                install_stack_requirements=False,
                install_deployment_requirements=False,
                disable_automatic_requirements_detection=True,
                replicate_local_python_environment=False,
                build_config=DockerBuildConfig(
                    build_options=DockerBuildOptions(platform="linux/amd64")
                ),
            ),
            "orchestrator": ModalOrchestratorSettings(
                synchronous=False,
                modal_environment=config.service.modal_environment,
                timeout=10800,
            ),
            "resources": ResourceSettings(cpu_count=2, memory="3GiB"),
        },
    )
    artifact = save_artifact(data=bundle, name="endless-baseline-task-bundle")
    configured(bundle_artifact_id=artifact.id, config=config)


if __name__ == "__main__":
    main()
