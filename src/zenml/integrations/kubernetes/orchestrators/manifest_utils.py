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

import base64
import json
import os
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple

from kubernetes import client as k8s_client

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_ENABLE_REPO_INIT_WARNINGS
from zenml.integrations.airflow.orchestrators.dag_generator import (
    ENV_ZENML_LOCAL_STORES_PATH,
)
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger

logger = get_logger(__name__)


def _create_image_pull_secret_data(
    registry_uri: str, username: str, password: str
) -> Dict[str, str]:
    """Create Docker registry authentication data for imagePullSecrets.

    Args:
        registry_uri: The registry URI (e.g., 'docker.io', 'gcr.io/project').
        username: The registry username.
        password: The registry password or token.

    Returns:
        Dictionary containing the base64-encoded .dockerconfigjson data.
    """
    # Normalize registry URI for Docker config - use the base registry domain
    # without path components for broader compatibility
    registry_server = registry_uri
    if registry_uri in ("docker.io", "index.docker.io"):
        registry_server = "https://index.docker.io/v1/"
    else:
        # Extract just the domain part for better image matching
        if registry_uri.startswith(("http://", "https://")):
            registry_server = registry_uri
        else:
            # For URIs like 'registry.onstackit.cloud/zenml', use just the domain
            domain = registry_uri.split("/")[0]
            registry_server = f"https://{domain}"

    # Create Docker config JSON - credentials are safely encoded in base64
    # This handles special characters that might cause issues in CLI usage
    docker_config = {
        "auths": {
            registry_server: {
                "username": username,
                "password": password,
                "auth": base64.b64encode(
                    f"{username}:{password}".encode()
                ).decode(),
            }
        }
    }

    return {
        ".dockerconfigjson": base64.b64encode(
            json.dumps(docker_config).encode()
        ).decode()
    }


def _get_container_registry_credentials(
    container_registry=None,
) -> List[Tuple[str, str, str]]:
    """Extract container registry credentials from the active stack.

    Args:
        container_registry: Optional container registry instance to use.
            If None, uses the container registry from the active stack.

    Returns:
        List of tuples containing (registry_uri, username, password) for each
        container registry that has credentials available.
    """
    credentials = []

    # If no container registry provided, get from active stack
    if container_registry is None:
        client = Client()
        stack = client.active_stack
        container_registry = stack.container_registry

    if not container_registry:
        return credentials

    # Use the new method from base container registry
    registry_data = container_registry.get_kubernetes_image_pull_secret_data()
    if registry_data:
        credentials.append(registry_data)

    return credentials


def _should_refresh_image_pull_secret(
    secret_name: str, namespace: str, core_api
) -> bool:
    """Check if an existing imagePullSecret needs to be refreshed.

    Args:
        secret_name: Name of the secret to check.
        namespace: Kubernetes namespace.
        core_api: Kubernetes Core API client.

    Returns:
        True if the secret should be refreshed, False otherwise.
    """
    try:
        secret = core_api.read_namespaced_secret(
            name=secret_name, namespace=namespace
        )

        # Check if secret has refresh annotations
        annotations = secret.metadata.annotations or {}
        refresh_after_str = annotations.get("zenml.io/refresh-after")

        if not refresh_after_str:
            # No refresh annotation, assume it needs refresh
            return True

        refresh_after = int(refresh_after_str)
        current_time = int(time.time())

        # Refresh if current time is past the refresh time
        return current_time >= refresh_after

    except Exception:
        # Secret doesn't exist or can't be read, needs creation
        return True


def _generate_image_pull_secrets(
    namespace: str = "default",
    container_registry=None,
    force_refresh: bool = False,
    core_api=None,
) -> Tuple[List[Dict[str, Any]], List[k8s_client.V1LocalObjectReference]]:
    """Generate Kubernetes secrets and references for container registry credentials.

    Args:
        namespace: The Kubernetes namespace to create secrets in.
        container_registry: Optional container registry instance to use.
            If None, uses the container registry from the active stack.
        force_refresh: If True, forces regeneration of secrets even if they exist.
        core_api: Optional Kubernetes Core API client for checking existing secrets.

    Returns:
        Tuple of (secret_manifests, local_object_references) where:
        - secret_manifests: List of Kubernetes secret manifests to create
        - local_object_references: List of V1LocalObjectReference objects for imagePullSecrets
    """
    credentials = _get_container_registry_credentials(container_registry)
    if not credentials:
        return [], []

    secret_manifests = []
    local_object_references = []

    # Check if credentials need refresh (for service connectors)
    needs_refresh = force_refresh
    if container_registry and hasattr(
        container_registry, "connector_has_expired"
    ):
        needs_refresh = (
            needs_refresh or container_registry.connector_has_expired()
        )

    for i, (registry_uri, username, password) in enumerate(credentials):
        # Create a unique secret name for this registry
        # Use registry URI to make it more descriptive and avoid conflicts
        safe_registry_name = registry_uri.replace(".", "-").replace("/", "-")
        secret_name = f"zenml-registry-{safe_registry_name}-{i}"[
            :63
        ]  # K8s name limit

        # Check if secret needs refresh
        should_refresh = needs_refresh or (
            core_api
            and _should_refresh_image_pull_secret(
                secret_name, namespace, core_api
            )
        )

        # Always add to local object references for pod spec
        local_object_references.append(
            k8s_client.V1LocalObjectReference(name=secret_name)
        )

        # Only include in manifests if it needs to be created/updated
        if not should_refresh:
            continue

        # Create the secret data
        secret_data = _create_image_pull_secret_data(
            registry_uri, username, password
        )

        # Add metadata for credential refresh tracking
        current_time = int(time.time())
        # Default refresh interval: 1 hour (3600 seconds)
        # This is conservative for most cloud providers that have longer-lived tokens
        refresh_interval = 3600

        # Create the secret manifest
        secret_manifest = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": secret_name,
                "namespace": namespace,
                "labels": {
                    "app.kubernetes.io/name": "zenml",
                    "app.kubernetes.io/component": "image-pull-secret",
                    "app.kubernetes.io/managed-by": "zenml",
                },
                "annotations": {
                    "zenml.io/created-at": str(current_time),
                    "zenml.io/refresh-after": str(
                        current_time + refresh_interval
                    ),
                    "zenml.io/registry-uri": registry_uri,
                },
            },
            "type": "kubernetes.io/dockerconfigjson",
            "data": secret_data,
        }

        secret_manifests.append(secret_manifest)

    return secret_manifests, local_object_references


def create_image_pull_secrets_from_manifests(
    secret_manifests: List[Dict[str, Any]],
    core_api,
    namespace: str,
    reuse_existing: bool = True,
) -> None:
    """Create imagePullSecrets from manifests with optional reuse logic.

    Args:
        secret_manifests: List of secret manifests to create.
        core_api: Kubernetes Core API client.
        namespace: Kubernetes namespace.
        reuse_existing: If True, reuses existing secrets and only creates new ones.
            If False, creates/updates all secrets.
    """
    for secret_manifest in secret_manifests:
        secret_name = secret_manifest["metadata"]["name"]

        if reuse_existing:
            # Check if secret already exists
            try:
                core_api.read_namespaced_secret(
                    name=secret_name, namespace=namespace
                )
                logger.debug(
                    f"imagePullSecret {secret_name} already exists, reusing it"
                )
                continue  # Skip creation, secret already exists
            except k8s_client.rest.ApiException as e:
                if e.status != 404:
                    # Some other error, re-raise
                    logger.warning(
                        f"Error checking existence of secret {secret_name}: {e}"
                    )
                    raise
                # Secret doesn't exist (404), proceed to create it

        # Create or update the secret
        try:
            kube_utils.create_or_update_secret_from_manifest(
                core_api=core_api,
                secret_manifest=secret_manifest,
            )
            logger.debug(
                f"Successfully created/updated imagePullSecret {secret_name}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create imagePullSecret {secret_name}: {e}"
            )
            raise


def cleanup_old_image_pull_secrets(
    core_api,
    namespace: str = "default",
    max_age_hours: int = 24,
) -> None:
    """Clean up old ZenML-managed imagePullSecrets.

    Args:
        core_api: Kubernetes Core API client.
        namespace: The Kubernetes namespace to clean up secrets in.
        max_age_hours: Maximum age in hours for secrets to be kept.
            Secrets older than this will be deleted.
    """
    try:
        # List all secrets in the namespace with ZenML labels
        secret_list = core_api.list_namespaced_secret(
            namespace=namespace,
            label_selector="app.kubernetes.io/managed-by=zenml,app.kubernetes.io/component=image-pull-secret",
        )

        current_time = int(time.time())
        max_age_seconds = max_age_hours * 3600

        for secret in secret_list.items:
            try:
                # Check if secret has creation time annotation
                annotations = secret.metadata.annotations or {}
                created_at_str = annotations.get("zenml.io/created-at")

                if not created_at_str:
                    # No creation time annotation, skip
                    continue

                created_at = int(created_at_str)
                age_seconds = current_time - created_at

                # Delete if older than max age
                if age_seconds > max_age_seconds:
                    logger.info(
                        f"Cleaning up old imagePullSecret {secret.metadata.name} "
                        f"(age: {age_seconds // 3600}h)"
                    )
                    core_api.delete_namespaced_secret(
                        name=secret.metadata.name,
                        namespace=namespace,
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to process secret {secret.metadata.name} for cleanup: {e}"
                )

    except Exception as e:
        logger.warning(f"Failed to cleanup old imagePullSecrets: {e}")


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
    owner_references: Optional[List[k8s_client.V1OwnerReference]] = None,
    auto_generate_image_pull_secrets: bool = True,
    namespace: str = "default",
    container_registry=None,
    core_api=None,
) -> Tuple[k8s_client.V1Pod, List[Dict[str, Any]]]:
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
        owner_references: List of owner references for the pod.
        auto_generate_image_pull_secrets: Whether to automatically generate
            imagePullSecrets from container registry credentials in the stack.
        namespace: The Kubernetes namespace to create secrets in.
        container_registry: Optional container registry instance to use.
            If None, uses the container registry from the active stack.
        core_api: Optional Kubernetes Core API client for checking existing secrets.

    Returns:
        Tuple of (pod_manifest, secret_manifests) where:
        - pod_manifest: The Kubernetes pod manifest
        - secret_manifests: List of secret manifests for imagePullSecrets
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
    # Handle imagePullSecrets - combine manual and auto-generated
    # This maintains backward compatibility by preserving existing manual configurations
    # while adding automatic registry authentication when available.
    image_pull_secrets = []
    secret_manifests = []

    # Add manually configured imagePullSecrets from pod_settings first
    # This ensures existing configurations continue to work unchanged
    if pod_settings and pod_settings.image_pull_secrets:
        image_pull_secrets.extend(
            [
                k8s_client.V1LocalObjectReference(name=name)
                for name in pod_settings.image_pull_secrets
            ]
        )

    # Auto-generate imagePullSecrets from container registry credentials
    if auto_generate_image_pull_secrets:
        try:
            generated_secrets, generated_refs = _generate_image_pull_secrets(
                namespace=namespace,
                container_registry=container_registry,
                core_api=core_api,
            )
            secret_manifests.extend(generated_secrets)
            image_pull_secrets.extend(generated_refs)
        except Exception as e:
            logger.warning(
                f"Failed to auto-generate imagePullSecrets from container "
                f"registry credentials: {e}. Falling back to manual configuration."
            )

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
            "run": kube_utils.sanitize_label(run_name),
            "pipeline": kube_utils.sanitize_label(pipeline_name),
        }
    )

    pod_metadata = k8s_client.V1ObjectMeta(
        name=pod_name,
        labels=labels,
        owner_references=owner_references,
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

    return pod_manifest, secret_manifests


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

        if settings.env:
            if container.env:
                container.env.extend(settings.env)
            else:
                container.env = settings.env

        if settings.env_from:
            if container.env_from:
                container.env_from.extend(settings.env_from)
            else:
                container.env_from = settings.env_from

    if settings.volumes:
        if pod_spec.volumes:
            pod_spec.volumes.extend(settings.volumes)
        else:
            pod_spec.volumes = settings.volumes

    if settings.host_ipc:
        pod_spec.host_ipc = settings.host_ipc

    if settings.scheduler_name:
        pod_spec.scheduler_name = settings.scheduler_name

    for key, value in settings.additional_pod_spec_args.items():
        if not hasattr(pod_spec, key):
            logger.warning(f"Ignoring invalid Pod Spec argument `{key}`.")
        else:
            if value is None:
                continue

            existing_value = getattr(pod_spec, key)
            if isinstance(existing_value, list):
                existing_value.extend(value)
            elif isinstance(existing_value, dict):
                existing_value.update(value)
            else:
                setattr(pod_spec, key, value)


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
    successful_jobs_history_limit: Optional[int] = None,
    failed_jobs_history_limit: Optional[int] = None,
    ttl_seconds_after_finished: Optional[int] = None,
    auto_generate_image_pull_secrets: bool = True,
    namespace: str = "default",
    container_registry=None,
    core_api=None,
) -> Tuple[k8s_client.V1CronJob, List[Dict[str, Any]]]:
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
        successful_jobs_history_limit: The number of successful jobs to retain.
        failed_jobs_history_limit: The number of failed jobs to retain.
        ttl_seconds_after_finished: The amount of seconds to keep finished jobs
            before deleting them.
        auto_generate_image_pull_secrets: Whether to automatically generate
            imagePullSecrets from container registry credentials in the stack.
        namespace: The Kubernetes namespace to create secrets in.
        container_registry: Optional container registry instance to use.
            If None, uses the container registry from the active stack.
        core_api: Optional Kubernetes Core API client for checking existing secrets.

    Returns:
        Tuple of (cron_job_manifest, secret_manifests) where:
        - cron_job_manifest: The Kubernetes CronJob manifest
        - secret_manifests: List of secret manifests for imagePullSecrets
    """
    pod_manifest, secret_manifests = build_pod_manifest(
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
        auto_generate_image_pull_secrets=auto_generate_image_pull_secrets,
        namespace=namespace,
        container_registry=container_registry,
        core_api=core_api,
    )

    job_spec = k8s_client.V1CronJobSpec(
        schedule=cron_expression,
        successful_jobs_history_limit=successful_jobs_history_limit,
        failed_jobs_history_limit=failed_jobs_history_limit,
        job_template=k8s_client.V1JobTemplateSpec(
            metadata=pod_manifest.metadata,
            spec=k8s_client.V1JobSpec(
                template=k8s_client.V1PodTemplateSpec(
                    metadata=pod_manifest.metadata,
                    spec=pod_manifest.spec,
                ),
                ttl_seconds_after_finished=ttl_seconds_after_finished,
            ),
        ),
    )

    job_manifest = k8s_client.V1CronJob(
        kind="CronJob",
        api_version="batch/v1",
        metadata=pod_manifest.metadata,
        spec=job_spec,
    )

    return job_manifest, secret_manifests


def build_role_binding_manifest_for_service_account(
    name: str,
    role_name: str,
    service_account_name: str,
    namespace: str = "default",
) -> Dict[str, Any]:
    """Build a manifest for a role binding of a service account.

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
        "kind": "RoleBinding",
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


def build_secret_manifest(
    name: str,
    data: Mapping[str, Optional[str]],
    secret_type: str = "Opaque",
) -> Dict[str, Any]:
    """Builds a Kubernetes secret manifest.

    Args:
        name: Name of the secret.
        data: The secret data.
        secret_type: The secret type.

    Returns:
        The secret manifest.
    """
    encoded_data = {
        key: base64.b64encode(value.encode()).decode() if value else None
        for key, value in data.items()
    }

    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": name,
        },
        "type": secret_type,
        "data": encoded_data,
    }
