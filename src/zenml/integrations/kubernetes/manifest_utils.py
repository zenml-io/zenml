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
import os
import sys
from typing import Any, Dict, List, Mapping, Optional

from kubernetes import client as k8s_client

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_ENABLE_REPO_INIT_WARNINGS
from zenml.integrations.airflow.orchestrators.dag_generator import (
    ENV_ZENML_LOCAL_STORES_PATH,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger

logger = get_logger(__name__)


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
    pod_name: Optional[str],
    image_name: str,
    command: List[str],
    args: List[str],
    privileged: bool,
    pod_settings: Optional[KubernetesPodSettings] = None,
    service_account_name: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    labels: Optional[Dict[str, str]] = None,
    mount_local_stores: bool = False,
    owner_references: Optional[List[k8s_client.V1OwnerReference]] = None,
    termination_grace_period_seconds: Optional[int] = 30,
) -> k8s_client.V1Pod:
    """Build a Kubernetes pod manifest for a ZenML run or step.

    Args:
        pod_name: Name of the pod.
        image_name: Name of the Docker image.
        command: Command to execute the entrypoint in the pod.
        args: Arguments provided to the entrypoint command.
        privileged: Whether to run the container in privileged mode.
        pod_settings: Optional settings for the pod.
        service_account_name: Optional name of a service account.
            Can be used to assign certain roles to a pod, e.g., to allow it to
            run Kubernetes commands from within the cluster.
        env: Environment variables to set.
        labels: Labels to add to the pod.
        mount_local_stores: Whether to mount the local stores path inside the
            pod.
        owner_references: List of owner references for the pod.
        termination_grace_period_seconds: The amount of seconds to wait for a
            pod to shutdown gracefully.

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
        termination_grace_period_seconds=termination_grace_period_seconds,
    )

    if service_account_name is not None:
        pod_spec.service_account_name = service_account_name

    # Apply pod settings if provided
    labels = labels or {}

    if pod_settings:
        add_pod_settings(pod_spec, pod_settings)

    if pod_settings and pod_settings.labels:
        labels.update(pod_settings.labels)

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


def pod_template_manifest_from_pod(
    pod: k8s_client.V1Pod,
) -> k8s_client.V1PodTemplateSpec:
    """Build a Kubernetes pod template manifest from a pod.

    Args:
        pod: The pod manifest to build the template from.

    Returns:
        The pod template manifest.
    """
    return k8s_client.V1PodTemplateSpec(
        metadata=pod.metadata,
        spec=pod.spec,
    )


def build_job_manifest(
    job_name: str,
    pod_template: k8s_client.V1PodTemplateSpec,
    backoff_limit: Optional[int] = None,
    ttl_seconds_after_finished: Optional[int] = None,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    active_deadline_seconds: Optional[int] = None,
    pod_failure_policy: Optional[Dict[str, Any]] = None,
    owner_references: Optional[List[k8s_client.V1OwnerReference]] = None,
) -> k8s_client.V1Job:
    """Build a Kubernetes job manifest.

    Args:
        job_name: Name of the job.
        pod_template: The pod template to use for the job.
        backoff_limit: The backoff limit for the job.
        ttl_seconds_after_finished: The TTL seconds after finished for the job.
        labels: The labels to use for the job.
        annotations: The annotations to use for the job.
        active_deadline_seconds: The active deadline seconds for the job.
        pod_failure_policy: The pod failure policy for the job.
        owner_references: The owner references for the job.

    Returns:
        The Kubernetes job manifest.
    """
    job_spec = k8s_client.V1JobSpec(
        template=pod_template,
        backoff_limit=backoff_limit,
        parallelism=1,
        ttl_seconds_after_finished=ttl_seconds_after_finished,
        active_deadline_seconds=active_deadline_seconds,
        pod_failure_policy=pod_failure_policy,
    )
    job_metadata = k8s_client.V1ObjectMeta(
        name=job_name,
        labels=labels,
        annotations=annotations,
        owner_references=owner_references,
    )

    return k8s_client.V1Job(spec=job_spec, metadata=job_metadata)


def job_template_manifest_from_job(
    job: k8s_client.V1Job,
) -> k8s_client.V1JobTemplateSpec:
    """Build a Kubernetes job template manifest from a job.

    Args:
        job: The job manifest to build the template from.

    Returns:
        The job template manifest.
    """
    return k8s_client.V1JobTemplateSpec(
        metadata=job.metadata,
        spec=job.spec,
    )


def build_cron_job_manifest(
    job_template: k8s_client.V1JobTemplateSpec,
    cron_expression: str,
    successful_jobs_history_limit: Optional[int] = None,
    failed_jobs_history_limit: Optional[int] = None,
) -> k8s_client.V1CronJob:
    """Build a Kubernetes cron job manifest.

    Args:
        job_template: The job template to use for the cron job.
        cron_expression: The cron expression to use for the cron job.
        successful_jobs_history_limit: The number of successful jobs to keep.
        failed_jobs_history_limit: The number of failed jobs to keep.

    Returns:
        The Kubernetes cron job manifest.
    """
    spec = k8s_client.V1CronJobSpec(
        schedule=cron_expression,
        successful_jobs_history_limit=successful_jobs_history_limit,
        failed_jobs_history_limit=failed_jobs_history_limit,
        job_template=job_template,
    )

    return k8s_client.V1CronJob(
        kind="CronJob",
        api_version="batch/v1",
        metadata=job_template.metadata,
        spec=spec,
    )


def build_deployment_manifest(
    deployment_name: str,
    namespace: str,
    labels: Dict[str, str],
    annotations: Optional[Dict[str, str]],
    replicas: int,
    image: str,
    command: List[str],
    args: List[str],
    env_vars: List[k8s_client.V1EnvVar],
    service_port: int,
    resource_requests: Dict[str, str],
    resource_limits: Dict[str, str],
    image_pull_policy: str,
    image_pull_secrets: List[str],
    service_account_name: Optional[str],
    liveness_probe_config: Dict[str, Any],
    readiness_probe_config: Dict[str, Any],
    pod_settings: Optional[Any] = None,
) -> k8s_client.V1Deployment:
    """Build a Kubernetes Deployment manifest.

    Args:
        deployment_name: Name of the deployment.
        namespace: Kubernetes namespace.
        labels: Labels to apply to resources.
        annotations: Annotations to apply to pod metadata.
        replicas: Number of pod replicas.
        image: Container image URI.
        command: Container command.
        args: Container arguments.
        env_vars: Environment variables for the container.
        service_port: Container port to expose.
        resource_requests: Resource requests (cpu, memory, gpu).
        resource_limits: Resource limits (cpu, memory, gpu).
        image_pull_policy: Image pull policy.
        image_pull_secrets: Names of image pull secrets.
        service_account_name: Service account name.
        liveness_probe_config: Liveness probe configuration.
        readiness_probe_config: Readiness probe configuration.
        pod_settings: Optional pod settings to apply.

    Returns:
        Kubernetes Deployment manifest.
    """
    container = k8s_client.V1Container(
        name="deployment",
        image=image,
        command=command,
        args=args,
        env=env_vars,
        ports=[
            k8s_client.V1ContainerPort(
                container_port=service_port,
                name="http",
            )
        ],
        resources=k8s_client.V1ResourceRequirements(
            requests=resource_requests,
            limits=resource_limits,
        ),
        liveness_probe=k8s_client.V1Probe(
            http_get=k8s_client.V1HTTPGetAction(
                path="/api/health",
                port=service_port,
            ),
            **liveness_probe_config,
        ),
        readiness_probe=k8s_client.V1Probe(
            http_get=k8s_client.V1HTTPGetAction(
                path="/api/health",
                port=service_port,
            ),
            **readiness_probe_config,
        ),
        image_pull_policy=image_pull_policy,
    )

    pod_spec = k8s_client.V1PodSpec(
        containers=[container],
        service_account_name=service_account_name,
        image_pull_secrets=[
            k8s_client.V1LocalObjectReference(name=secret_name)
            for secret_name in image_pull_secrets
        ]
        if image_pull_secrets
        else None,
    )

    # Apply pod settings if provided
    if pod_settings:
        add_pod_settings(pod_spec, pod_settings)

    # Pod template labels must include the selector label
    pod_labels = {**labels, "app": deployment_name}

    pod_template = k8s_client.V1PodTemplateSpec(
        metadata=k8s_client.V1ObjectMeta(
            labels=pod_labels,
            annotations=annotations or None,
        ),
        spec=pod_spec,
    )

    return k8s_client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=k8s_client.V1ObjectMeta(
            name=deployment_name,
            namespace=namespace,
            labels=labels,
        ),
        spec=k8s_client.V1DeploymentSpec(
            replicas=replicas,
            selector=k8s_client.V1LabelSelector(
                match_labels={"app": deployment_name}
            ),
            template=pod_template,
        ),
    )


def build_service_manifest(
    service_name: str,
    namespace: str,
    labels: Dict[str, str],
    annotations: Optional[Dict[str, str]],
    service_type: str,
    service_port: int,
    node_port: Optional[int],
    session_affinity: Optional[str],
    load_balancer_ip: Optional[str],
    load_balancer_source_ranges: Optional[List[str]],
) -> k8s_client.V1Service:
    """Build a Kubernetes Service manifest.

    Args:
        service_name: Name of the service.
        namespace: Kubernetes namespace.
        labels: Labels to apply to the service.
        annotations: Annotations to apply to the service.
        service_type: Type of service (LoadBalancer, NodePort, ClusterIP).
        service_port: Port to expose.
        node_port: Node port (for NodePort service type).
        session_affinity: Session affinity setting.
        load_balancer_ip: Static IP for LoadBalancer.
        load_balancer_source_ranges: CIDR blocks for LoadBalancer.

    Returns:
        Kubernetes Service manifest.
    """
    service_port_obj = k8s_client.V1ServicePort(
        port=service_port,
        target_port=service_port,
        protocol="TCP",
        name="http",
    )

    if service_type == "NodePort" and node_port:
        service_port_obj.node_port = node_port

    service_spec = k8s_client.V1ServiceSpec(
        type=service_type,
        selector={"app": service_name},
        ports=[service_port_obj],
    )

    if session_affinity:
        service_spec.session_affinity = session_affinity

    if service_type == "LoadBalancer":
        if load_balancer_ip:
            service_spec.load_balancer_ip = load_balancer_ip
        if load_balancer_source_ranges:
            service_spec.load_balancer_source_ranges = (
                load_balancer_source_ranges
            )

    return k8s_client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=k8s_client.V1ObjectMeta(
            name=service_name,
            namespace=namespace,
            labels=labels,
            annotations=annotations or None,
        ),
        spec=service_spec,
    )


def build_ingress_manifest(
    ingress_name: str,
    namespace: str,
    labels: Dict[str, str],
    annotations: Optional[Dict[str, str]],
    service_name: str,
    service_port: int,
    ingress_class: Optional[str],
    ingress_host: Optional[str],
    ingress_path: str,
    ingress_path_type: str,
    tls_enabled: bool,
    tls_secret_name: Optional[str],
) -> k8s_client.V1Ingress:
    """Build a Kubernetes Ingress manifest.

    Args:
        ingress_name: Name of the ingress.
        namespace: Kubernetes namespace.
        labels: Labels to apply to the ingress.
        annotations: Annotations to apply to the ingress.
        service_name: Name of the backend service.
        service_port: Port of the backend service.
        ingress_class: Ingress class name.
        ingress_host: Hostname for the ingress rule.
        ingress_path: Path for the ingress rule.
        ingress_path_type: Path type (Prefix, Exact, etc.).
        tls_enabled: Whether TLS is enabled.
        tls_secret_name: Name of the TLS secret.

    Returns:
        Kubernetes Ingress manifest.
    """
    backend = k8s_client.V1IngressBackend(
        service=k8s_client.V1IngressServiceBackend(
            name=service_name,
            port=k8s_client.V1ServiceBackendPort(number=service_port),
        )
    )

    http_ingress_path = k8s_client.V1HTTPIngressPath(
        path=ingress_path,
        path_type=ingress_path_type,
        backend=backend,
    )

    http_ingress_rule_value = k8s_client.V1HTTPIngressRuleValue(
        paths=[http_ingress_path]
    )

    ingress_rule = k8s_client.V1IngressRule(
        http=http_ingress_rule_value,
    )

    if ingress_host:
        ingress_rule.host = ingress_host

    tls_configs = None
    if tls_enabled and tls_secret_name:
        tls_config = k8s_client.V1IngressTLS(
            secret_name=tls_secret_name,
        )
        if ingress_host:
            tls_config.hosts = [ingress_host]
        tls_configs = [tls_config]

    ingress_spec = k8s_client.V1IngressSpec(
        rules=[ingress_rule],
        tls=tls_configs,
    )

    if ingress_class:
        ingress_spec.ingress_class_name = ingress_class

    return k8s_client.V1Ingress(
        api_version="networking.k8s.io/v1",
        kind="Ingress",
        metadata=k8s_client.V1ObjectMeta(
            name=ingress_name,
            namespace=namespace,
            labels=labels,
            annotations=annotations or None,
        ),
        spec=ingress_spec,
    )
