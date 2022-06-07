"""Utility functions for building manifests for k8s pods."""

from typing import Any, Dict, List

from zenml.constants import ENV_ZENML_ENABLE_REPO_INIT_WARNINGS


def build_base_pod_manifest(
    run_name: str, pipeline_name: str, image_name: str
) -> Dict[str, Any]:
    """Build a basic k8s pod manifest.

    This includes only the data that stays the same for each step manifest.
    To add in the step-specific data, use `update_pod_manifest()` after.

    Args:
        run_name (str): Name of the ZenML run.
        pipeline_name (str): Name of the ZenML pipeline.
        image_name (str): Name of the Docker image.

    Returns:
        Dict[str, Any]: Base pod manifest.
    """
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": None,  # to be set in update_pod_manifest
            "labels": {
                "run": run_name,
                "pipeline": pipeline_name,
            },
        },
        "spec": {
            "restartPolicy": "Never",
            "containers": [
                {
                    "name": "main",
                    "image": image_name,
                    "command": None,  # to be set in update_pod_manifest
                    "args": None,  # to be set in update_pod_manifest
                    "env": [
                        {
                            "name": ENV_ZENML_ENABLE_REPO_INIT_WARNINGS,
                            "value": "False",
                        }
                    ],
                }
            ],
        },
    }


def update_pod_manifest(
    base_pod_manifest: Dict[str, Any],
    pod_name: str,
    command: List[str],
    args: List[str],
) -> Dict[str, Any]:
    """Add step-specific arguments to a k8s pod manifest.

    Args:
        base_pod_manifest (Dict[str, Any]): General pod manifest created by
            `build_base_pod_manifest()`.
        pod_name (str): Name of the pod.
        command (List[str]): Command to execute the entrypoint in the pod.
        args (List[str]): Arguments provided to the entrypoint command.

    Returns:
        Dict[str, Any]: Updated pod manifest.
    """
    pod_manifest = base_pod_manifest.copy()
    pod_manifest["metadata"]["name"] = pod_name
    pod_manifest["spec"]["containers"][0]["command"] = command
    pod_manifest["spec"]["containers"][0]["args"] = args
    return pod_manifest
