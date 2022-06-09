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


def build_persistent_volume_claim_manifest(
    name: str = "mysql-pv-claim",
    namespace: str = "default",
    storage_request: str = "10Gi",
) -> Dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "spec": {
            "storageClassName": "manual",
            "accessModes": ["ReadWriteOnce"],
            "resources": {
                "requests": {
                    "storage": storage_request,
                }
            },
        },
    }


def build_persistent_volume_manifest(
    name: str = "mysql-pv-volume",
    namespace: str = "default",
    storage_capacity: str = "10Gi",
    path: str = "/mnt/data",
) -> Dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "PersistentVolume",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {"type": "local"},
        },
        "spec": {
            "storageClassName": "manual",
            "capacity": {"storage": storage_capacity},
            "accessModes": ["ReadWriteOnce"],
            "hostPath": {"path": path},
        },
    }


def build_mysql_deployment_manifest(
    name: str = "mysql",
    namespace: str = "default",
    port: int = 3306,  # MYSQL default port; don't change!
    pv_claim_name: str = "mysql-pv-claim",
) -> Dict[str, Any]:
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "selector": {
                "matchLabels": {
                    "app": name,
                },
            },
            "strategy": {
                "type": "Recreate",
            },
            "template": {
                "metadata": {
                    "labels": {"app": name},
                },
                "spec": {
                    "containers": [
                        {
                            "image": "gcr.io/ml-pipeline/mysql:5.6",
                            "name": name,
                            "env": [
                                {
                                    "name": "MYSQL_ALLOW_EMPTY_PASSWORD",
                                    "value": '"true"',
                                }
                            ],
                            "ports": [{"containerPort": port, "name": name}],
                            "volumeMounts": [
                                {
                                    "name": "mysql-persistent-storage",
                                    "mountPath": "/var/lib/mysql",
                                }
                            ],
                        }
                    ],
                    "volumes": [
                        {
                            "name": "mysql-persistent-storage",
                            "persistentVolumeClaim": {
                                "claimName": pv_claim_name
                            },
                        }
                    ],
                },
            },
        },
    }


def build_mysql_service_manifest(
    name: str = "mysql",
    namespace: str = "default",
    port: int = 3306,  # MYSQL default port; don't change!
) -> Dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "spec": {
            "selector": {"app": "mysql"},
            "clusterIP": "None",
            "ports": [{"port": port}],
        },
    }


def build_cluster_role_binding_manifest_for_service_account(
    name: str = "zenml-edit",
    namespace: str = "default",
    service_account_name: str = "zenml-service-account",
    role_name: str = "edit",
) -> Dict[str, Any]:

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
    name: str = "zenml-service-account", namespace: str = "default"
) -> Dict[str, Any]:
    return {
        "apiVersion": "v1",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
    }


def build_namespace_manifest(
    namespace: str = "zenml"
):
    return {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": namespace,
        }
    }
