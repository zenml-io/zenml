"""Submit the native training pilot with an uploaded bundle artifact."""

import argparse
from pathlib import Path

from native_training import (
    NativeTrainingConfig,
    endless_terminals_native_training,
)
from sandbox_pipeline import load_bundle_task

from zenml import save_artifact
from zenml.client import Client
from zenml.config import DockerSettings
from zenml.config.docker_settings import DockerBuildConfig, DockerBuildOptions
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings


def main() -> None:
    """Validate the active stack and submit the native training pipeline.

    Raises:
        RuntimeError: The active stack lacks Kubernetes orchestration or sandbox.
        ValueError: The bundle directory is missing.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--service-account", required=True)
    args = parser.parse_args()
    config = NativeTrainingConfig.model_validate_json(args.config.read_text())
    bundle = args.bundle.resolve()
    if not bundle.is_dir() or not (bundle / "task-manifest.json").is_file():
        raise ValueError("--bundle must contain task-manifest.json")
    load_bundle_task(bundle, config.sandbox)
    stack = Client().active_stack
    if (
        stack.orchestrator.flavor != "kubernetes"
        or stack.sandbox is None
        or stack.sandbox.flavor != "kubernetes"
    ):
        raise RuntimeError(
            "Select a stack with Kubernetes orchestrator and Kubernetes sandbox"
        )
    placement = KubernetesPodSettings(
        node_selectors={"pool": "workloads"},
        tolerations=[
            {
                "key": "pool",
                "operator": "Equal",
                "value": "workloads",
                "effect": "NoSchedule",
            }
        ],
        resources={
            "requests": {"cpu": "500m", "memory": "1Gi"},
            "limits": {"cpu": "2", "memory": "3Gi"},
        },
    )
    configured = endless_terminals_native_training.with_options(
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
            "orchestrator": KubernetesOrchestratorSettings(
                synchronous=False,
                max_parallelism=1,
                ttl_seconds_after_finished=3600,
                active_deadline_seconds=10800,
                service_account_name=args.service_account,
                step_pod_service_account_name=args.service_account,
                pod_settings=placement,
                orchestrator_pod_settings=placement,
            ),
        },
    )
    artifact = save_artifact(
        data=bundle, name="endless-native-training-task-bundle"
    )
    configured(bundle_artifact_id=artifact.id, config=config)


if __name__ == "__main__":
    main()
