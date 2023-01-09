#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Utility functions for building manifests for k8s pods."""

from typing import Any, Dict, List, Optional

from zenml.constants import ENV_ZENML_ENABLE_REPO_INIT_WARNINGS
from zenml.integrations.kubernetes.flavors import KubernetesOrchestratorSettings
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings


def build_pod_manifest(
    pod_name: str,
    run_name: str,
    pipeline_name: str,
    image_name: str,
    command: List[str],
    args: List[str],
    settings: KubernetesOrchestratorSettings,
    service_account_name: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Build a Kubernetes pod manifest for a ZenML run or step.

    Args:
        pod_name: Name of the pod.
        run_name: Name of the ZenML run.
        pipeline_name: Name of the ZenML pipeline.
        image_name: Name of the Docker image.
        command: Command to execute the entrypoint in the pod.
        args: Arguments provided to the entrypoint command.
        settings: `KubernetesOrchestratorSettings` object
        service_account_name: Optional name of a service account.
            Can be used to assign certain roles to a pod, e.g., to allow it to
            run Kubernetes commands from within the cluster.
        env: Environment variables to set.

    Returns:
        Pod manifest.
    """
    env = env.copy() if env else {}
    env.setdefault(ENV_ZENML_ENABLE_REPO_INIT_WARNINGS, "False")

    spec: Dict[str, Any] = {
        "restartPolicy": "Never",
        "containers": [
            {
                "name": "main",
                "image": image_name,
                "command": command,
                "args": args,
                "env": [
                    {"name": name, "value": value}
                    for name, value in env.items()
                ],
            }
        ],
    }

    if service_account_name is not None:
        spec["serviceAccountName"] = service_account_name

    if settings.pod_settings:
        spec.update(add_pod_settings(settings.pod_settings))

    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": pod_name,
            "labels": {
                "run": run_name,
                "pipeline": pipeline_name,
            },
        },
        "spec": spec,
    }

    return manifest


def add_pod_settings(
    settings: KubernetesPodSettings,
) -> Dict[str, Any]:
    """Updates `spec` fields in pod if passed in orchestrator settings.

    Args:
        settings: Pod settings to apply.

    Returns:
        Dictionary with additional fields for the pod
    """
    spec: Dict[str, Any] = {}

    if settings.node_selectors:
        spec["nodeSelector"] = settings.node_selectors

    if settings.affinity:
        spec["affinity"] = settings.affinity

    if settings.tolerations:
        spec["tolerations"] = settings.tolerations

    return spec


def build_cron_job_manifest(
    cron_expression: str,
    pod_name: str,
    run_name: str,
    pipeline_name: str,
    image_name: str,
    command: List[str],
    args: List[str],
    settings: KubernetesOrchestratorSettings,
    service_account_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a manifest for launching a pod as scheduled CRON job.

    Args:
        cron_expression: CRON job schedule expression, e.g. "* * * * *".
        pod_name: Name of the pod.
        run_name: Name of the ZenML run.
        pipeline_name: Name of the ZenML pipeline.
        image_name: Name of the Docker image.
        command: Command to execute the entrypoint in the pod.
        args: Arguments provided to the entrypoint command.
        settings: `KubernetesOrchestratorSettings` object
        service_account_name: Optional name of a service account.
            Can be used to assign certain roles to a pod, e.g., to allow it to
            run Kubernetes commands from within the cluster.

    Returns:
        CRON job manifest.
    """
    pod_manifest = build_pod_manifest(
        pod_name=pod_name,
        run_name=run_name,
        pipeline_name=pipeline_name,
        image_name=image_name,
        command=command,
        args=args,
        settings=settings,
        service_account_name=service_account_name,
    )
    return {
        "apiVersion": "batch/v1beta1",
        "kind": "CronJob",
        "metadata": pod_manifest["metadata"],
        "spec": {
            "schedule": cron_expression,
            "jobTemplate": {
                "metadata": pod_manifest["metadata"],
                "spec": {"template": {"spec": pod_manifest["spec"]}},
            },
        },
    }


def build_cluster_role_binding_manifest_for_service_account(
    name: str,
    role_name: str,
    service_account_name: str,
    namespace: str = "default",
) -> Dict[str, Any]:
    """Build a manifest for a cluster role binding of a service account.

    Args:
        name: Name of the cluster role binding.
        role_name: Name of the role.
        service_account_name: Name of the service account.
        namespace: Kubernetes namespace. Defaults to "default".

    Returns:
        Manifest for a cluster role binding of a service account.
    """
    return {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "ClusterRoleBinding",
        "metadata": {"name": name},
        "subjects": [
            {
                "kind": "ServiceAccount",
                "name": service_account_name,
                "namespace": namespace,
            }
        ],
        "roleRef": {
            "kind": "ClusterRole",
            "name": role_name,
            "apiGroup": "rbac.authorization.k8s.io",
        },
    }


def build_service_account_manifest(
    name: str, namespace: str = "default"
) -> Dict[str, Any]:
    """Build the manifest for a service account.

    Args:
        name: Name of the service account.
        namespace: Kubernetes namespace. Defaults to "default".

    Returns:
        Manifest for a service account.
    """
    return {
        "apiVersion": "v1",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
    }


def build_namespace_manifest(namespace: str) -> Dict[str, Any]:
    """Build the manifest for a new namespace.

    Args:
        namespace: Kubernetes namespace.

    Returns:
        Manifest of the new namespace.
    """
    return {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": namespace,
        },
    }
