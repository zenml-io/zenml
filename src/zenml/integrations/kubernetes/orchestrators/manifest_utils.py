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

import os
import sys
from typing import Any, Dict, List, Optional

from kubernetes import client as k8s_client

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_ENABLE_REPO_INIT_WARNINGS
from zenml.integrations.airflow.orchestrators.dag_generator import (
    ENV_ZENML_LOCAL_STORES_PATH,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings


def add_local_stores_mount(
    pod_spec: k8s_client.V1PodSpec,
) -> None:
    """Makes changes in place to the configuration of the pod spec.

    Configures mounted volumes for stack components that write to a local
    path.

    Args:
        pod_spec: The pod spec to update.
    """
    assert len(pod_spec.containers) == 1
    container_spec: k8s_client.V1Container = pod_spec.containers[0]

    stack = Client().active_stack

    stack.check_local_paths()

    local_stores_path = GlobalConfiguration().local_stores_path

    host_path = k8s_client.V1HostPathVolumeSource(
        path=local_stores_path, type="Directory"
    )

    pod_spec.volumes = pod_spec.volumes or []
    pod_spec.volumes.append(
        k8s_client.V1Volume(
            name="local-stores",
            host_path=host_path,
        )
    )
    container_spec.volume_mounts = container_spec.volume_mounts or []
    container_spec.volume_mounts.append(
        k8s_client.V1VolumeMount(
            name="local-stores",
            mount_path=local_stores_path,
        )
    )

    if sys.platform == "win32":
        # File permissions are not checked on Windows. This if clause
        # prevents mypy from complaining about unused 'type: ignore'
        # statements
        pass
    else:
        # Run KFP containers in the context of the local UID/GID
        # to ensure that the local stores can be shared
        # with the local pipeline runs.
        pod_spec.security_context = k8s_client.V1SecurityContext(
            run_as_user=os.getuid(),
            run_as_group=os.getgid(),
        )

    container_spec.env = container_spec.env or []
    container_spec.env.append(
        k8s_client.V1EnvVar(
            name=ENV_ZENML_LOCAL_STORES_PATH,
            value=local_stores_path,
        )
    )


def build_pod_manifest(
    pod_name: str,
    run_name: str,
    pipeline_name: str,
    image_name: str,
    command: List[str],
    args: List[str],
    privileged: bool,
    pod_settings: Optional[KubernetesPodSettings] = None,
    service_account_name: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    mount_local_stores: bool = False,
) -> k8s_client.V1Pod:
    """Build a Kubernetes pod manifest for a ZenML run or step.

    Args:
        pod_name: Name of the pod.
        run_name: Name of the ZenML run.
        pipeline_name: Name of the ZenML pipeline.
        image_name: Name of the Docker image.
        command: Command to execute the entrypoint in the pod.
        args: Arguments provided to the entrypoint command.
        privileged: Whether to run the container in privileged mode.
        pod_settings: Optional settings for the pod.
        service_account_name: Optional name of a service account.
            Can be used to assign certain roles to a pod, e.g., to allow it to
            run Kubernetes commands from within the cluster.
        env: Environment variables to set.
        mount_local_stores: Whether to mount the local stores path inside the
            pod.

    Returns:
        Pod manifest.
    """
    env = env.copy() if env else {}
    env.setdefault(ENV_ZENML_ENABLE_REPO_INIT_WARNINGS, "False")

    security_context = k8s_client.V1SecurityContext(privileged=privileged)
    container_spec = k8s_client.V1Container(
        name="main",
        image=image_name,
        command=command,
        args=args,
        env=[
            k8s_client.V1EnvVar(name=name, value=value)
            for name, value in env.items()
        ],
        security_context=security_context,
    )
    image_pull_secrets = []
    if pod_settings:
        image_pull_secrets = [
            k8s_client.V1LocalObjectReference(name=name)
            for name in pod_settings.image_pull_secrets
        ]

    pod_spec = k8s_client.V1PodSpec(
        containers=[container_spec],
        restart_policy="Never",
        image_pull_secrets=image_pull_secrets,
    )

    if service_account_name is not None:
        pod_spec.service_account_name = service_account_name

    labels = {}

    if pod_settings:
        add_pod_settings(pod_spec, pod_settings)

        # Add pod_settings.labels to the labels
        if pod_settings.labels:
            labels.update(pod_settings.labels)

    # Add run_name and pipeline_name to the labels
    labels.update(
        {
            "run": run_name,
            "pipeline": pipeline_name,
        }
    )

    pod_metadata = k8s_client.V1ObjectMeta(
        name=pod_name,
        labels=labels,
    )

    if pod_settings and pod_settings.annotations:
        pod_metadata.annotations = pod_settings.annotations

    pod_manifest = k8s_client.V1Pod(
        kind="Pod",
        api_version="v1",
        metadata=pod_metadata,
        spec=pod_spec,
    )

    if mount_local_stores:
        add_local_stores_mount(pod_spec)

    return pod_manifest


def add_pod_settings(
    pod_spec: k8s_client.V1PodSpec,
    settings: KubernetesPodSettings,
) -> None:
    """Updates pod `spec` fields in place if passed in orchestrator settings.

    Args:
        pod_spec: Pod spec to update.
        settings: Pod settings to apply.
    """
    if settings.node_selectors:
        pod_spec.node_selector = settings.node_selectors

    if settings.affinity:
        pod_spec.affinity = settings.affinity

    if settings.tolerations:
        pod_spec.tolerations = settings.tolerations

    for container in pod_spec.containers:
        assert isinstance(container, k8s_client.V1Container)
        container._resources = settings.resources
        if settings.volume_mounts:
            if container.volume_mounts:
                container.volume_mounts.extend(settings.volume_mounts)
            else:
                container.volume_mounts = settings.volume_mounts

    if settings.volumes:
        if pod_spec.volumes:
            pod_spec.volumes.extend(settings.volumes)
        else:
            pod_spec.volumes = settings.volumes

    if settings.host_ipc:
        pod_spec.host_ipc = settings.host_ipc


def build_cron_job_manifest(
    cron_expression: str,
    pod_name: str,
    run_name: str,
    pipeline_name: str,
    image_name: str,
    command: List[str],
    args: List[str],
    privileged: bool,
    pod_settings: Optional[KubernetesPodSettings] = None,
    service_account_name: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    mount_local_stores: bool = False,
) -> k8s_client.V1CronJob:
    """Create a manifest for launching a pod as scheduled CRON job.

    Args:
        cron_expression: CRON job schedule expression, e.g. "* * * * *".
        pod_name: Name of the pod.
        run_name: Name of the ZenML run.
        pipeline_name: Name of the ZenML pipeline.
        image_name: Name of the Docker image.
        command: Command to execute the entrypoint in the pod.
        args: Arguments provided to the entrypoint command.
        privileged: Whether to run the container in privileged mode.
        pod_settings: Optional settings for the pod.
        service_account_name: Optional name of a service account.
            Can be used to assign certain roles to a pod, e.g., to allow it to
            run Kubernetes commands from within the cluster.
        env: Environment variables to set.
        mount_local_stores: Whether to mount the local stores path inside the
            pod.

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
        privileged=privileged,
        pod_settings=pod_settings,
        service_account_name=service_account_name,
        env=env,
        mount_local_stores=mount_local_stores,
    )

    job_spec = k8s_client.V1CronJobSpec(
        schedule=cron_expression,
        job_template=k8s_client.V1JobTemplateSpec(
            metadata=pod_manifest.metadata,
            spec=k8s_client.V1JobSpec(
                template=k8s_client.V1PodTemplateSpec(
                    metadata=pod_manifest.metadata,
                    spec=pod_manifest.spec,
                ),
            ),
        ),
    )

    job_manifest = k8s_client.V1CronJob(
        kind="CronJob",
        api_version="batch/v1",
        metadata=pod_manifest.metadata,
        spec=job_spec,
    )

    return job_manifest


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
