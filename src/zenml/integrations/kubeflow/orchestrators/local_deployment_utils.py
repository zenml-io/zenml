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
"""Utils for the local Kubeflow deployment behaviors."""

import json
import shutil
import subprocess
import sys
import time

from zenml.config.global_config import GlobalConfiguration
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import networking_utils, yaml_utils

KFP_VERSION = "1.8.1"
# Name of the K3S image to use for the local K3D cluster.
# The version (e.g. v1.23.5) refers to a specific kubernetes release and is
# fixed as KFP doesn't support the newest releases immediately.
K3S_IMAGE_NAME = "rancher/k3s:v1.23.5-k3s1"

logger = get_logger(__name__)


def check_prerequisites(
    skip_k3d: bool = False, skip_kubectl: bool = False
) -> bool:
    """Checks prerequisites for a local kubeflow pipelines deployment.

    It makes sure they are installed.

    Args:
        skip_k3d: Whether to skip the check for the k3d command.
        skip_kubectl: Whether to skip the check for the kubectl command.

    Returns:
        Whether all prerequisites are installed.
    """
    k3d_installed = skip_k3d or shutil.which("k3d") is not None
    kubectl_installed = skip_kubectl or shutil.which("kubectl") is not None
    logger.debug(
        "Local kubeflow deployment prerequisites: K3D - %s, Kubectl - %s",
        k3d_installed,
        kubectl_installed,
    )
    return k3d_installed and kubectl_installed


def write_local_registry_yaml(
    yaml_path: str, registry_name: str, registry_uri: str
) -> None:
    """Writes a K3D registry config file.

    Args:
        yaml_path: Path where the config file should be written to.
        registry_name: Name of the registry.
        registry_uri: URI of the registry.
    """
    yaml_content = {
        "mirrors": {registry_uri: {"endpoint": [f"http://{registry_name}"]}}
    }
    yaml_utils.write_yaml(yaml_path, yaml_content)


def k3d_cluster_exists(cluster_name: str) -> bool:
    """Checks whether there exists a K3D cluster with the given name.

    Args:
        cluster_name: Name of the cluster to check.

    Returns:
        Whether the cluster exists.
    """
    output = subprocess.check_output(
        ["k3d", "cluster", "list", "--output", "json"]
    )
    clusters = json.loads(output)
    for cluster in clusters:
        if cluster["name"] == cluster_name:
            return True
    return False


def k3d_cluster_running(cluster_name: str) -> bool:
    """Checks whether the K3D cluster with the given name is running.

    Args:
        cluster_name: Name of the cluster to check.

    Returns:
        Whether the cluster is running.
    """
    output = subprocess.check_output(
        ["k3d", "cluster", "list", "--output", "json"]
    )
    clusters = json.loads(output)
    for cluster in clusters:
        if cluster["name"] == cluster_name:
            server_count: int = cluster["serversCount"]
            servers_running: int = cluster["serversRunning"]
            return servers_running == server_count
    return False


def create_k3d_cluster(
    cluster_name: str, registry_name: str, registry_config_path: str
) -> None:
    """Creates a K3D cluster.

    Args:
        cluster_name: Name of the cluster to create.
        registry_name: Name of the registry to create for this cluster.
        registry_config_path: Path to the registry config file.
    """
    logger.info("Creating local K3D cluster '%s'.", cluster_name)
    local_stores_path = GlobalConfiguration().local_stores_path
    subprocess.check_call(
        [
            "k3d",
            "cluster",
            "create",
            cluster_name,
            "--image",
            K3S_IMAGE_NAME,
            "--registry-create",
            registry_name,
            "--registry-config",
            registry_config_path,
            "--volume",
            f"{local_stores_path}:{local_stores_path}",
        ]
    )
    logger.info("Finished K3D cluster creation.")


def start_k3d_cluster(cluster_name: str) -> None:
    """Starts a K3D cluster with the given name.

    Args:
        cluster_name: Name of the cluster to start.
    """
    subprocess.check_call(["k3d", "cluster", "start", cluster_name])
    logger.info("Started local k3d cluster '%s'.", cluster_name)


def stop_k3d_cluster(cluster_name: str) -> None:
    """Stops a K3D cluster with the given name.

    Args:
        cluster_name: Name of the cluster to stop.
    """
    subprocess.check_call(["k3d", "cluster", "stop", cluster_name])
    logger.info("Stopped local k3d cluster '%s'.", cluster_name)


def delete_k3d_cluster(cluster_name: str) -> None:
    """Deletes a K3D cluster with the given name.

    Args:
        cluster_name: Name of the cluster to delete.
    """
    subprocess.check_call(["k3d", "cluster", "delete", cluster_name])
    logger.info("Deleted local k3d cluster '%s'.", cluster_name)


def kubeflow_pipelines_ready(kubernetes_context: str) -> bool:
    """Returns whether all Kubeflow Pipelines pods are ready.

    Args:
        kubernetes_context: The kubernetes context in which the pods
            should be checked.

    Returns:
        Whether all Kubeflow Pipelines pods are ready.
    """
    try:
        subprocess.check_call(
            [
                "kubectl",
                "--context",
                kubernetes_context,
                "--namespace",
                "kubeflow",
                "wait",
                "--for",
                "condition=ready",
                "--timeout=0s",
                "pods",
                "-l",
                "application-crd-id=kubeflow-pipelines",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def wait_until_kubeflow_pipelines_ready(kubernetes_context: str) -> None:
    """Waits until all Kubeflow Pipelines pods are ready.

    Args:
        kubernetes_context: The kubernetes context in which the pods
            should be checked.
    """
    logger.info(
        "Waiting for all Kubeflow Pipelines pods to be ready (this might "
        "take a few minutes)."
    )
    while True:
        logger.info("Current pod status:")
        subprocess.check_call(
            [
                "kubectl",
                "--context",
                kubernetes_context,
                "--namespace",
                "kubeflow",
                "get",
                "pods",
            ]
        )
        if kubeflow_pipelines_ready(kubernetes_context=kubernetes_context):
            break

        logger.info(
            "One or more pods not ready yet, waiting for 30 seconds..."
        )
        time.sleep(30)


def deploy_kubeflow_pipelines(kubernetes_context: str) -> None:
    """Deploys Kubeflow Pipelines.

    Args:
        kubernetes_context: The kubernetes context on which Kubeflow Pipelines
            should be deployed.
    """
    logger.info("Deploying Kubeflow Pipelines.")
    subprocess.check_call(
        [
            "kubectl",
            "--context",
            kubernetes_context,
            "apply",
            "-k",
            f"github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref={KFP_VERSION}&timeout=5m",
        ]
    )
    subprocess.check_call(
        [
            "kubectl",
            "--context",
            kubernetes_context,
            "wait",
            "--timeout=60s",
            "--for",
            "condition=established",
            "crd/applications.app.k8s.io",
        ]
    )
    subprocess.check_call(
        [
            "kubectl",
            "--context",
            kubernetes_context,
            "apply",
            "-k",
            f"github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic-pns?ref={KFP_VERSION}&timeout=5m",
        ]
    )

    wait_until_kubeflow_pipelines_ready(kubernetes_context=kubernetes_context)
    logger.info("Finished Kubeflow Pipelines setup.")


def add_hostpath_to_kubeflow_pipelines(
    kubernetes_context: str, local_path: str
) -> None:
    """Patches the Kubeflow Pipelines deployment to mount a local folder.

    This folder serves as a hostpath for visualization purposes.

    This function reconfigures the Kubeflow pipelines deployment to use a
    shared local folder to support loading the TensorBoard viewer and other
    pipeline visualization results from a local artifact store, as described
    here:

    https://github.com/kubeflow/pipelines/blob/master/docs/config/volume-support.md

    Args:
        kubernetes_context: The kubernetes context on which Kubeflow Pipelines
            should be patched.
        local_path: The path to the local folder to mount as a hostpath.
    """
    logger.info("Patching Kubeflow Pipelines to mount a local folder.")

    pod_template = {
        "spec": {
            "serviceAccountName": "kubeflow-pipelines-viewer",
            "containers": [
                {
                    "volumeMounts": [
                        {
                            "mountPath": local_path,
                            "name": "local-artifact-store",
                        }
                    ]
                }
            ],
            "volumes": [
                {
                    "hostPath": {
                        "path": local_path,
                        "type": "Directory",
                    },
                    "name": "local-artifact-store",
                }
            ],
        }
    }
    pod_template_json = json.dumps(pod_template, indent=2)
    config_map_data = {"data": {"viewer-pod-template.json": pod_template_json}}
    config_map_data_json = json.dumps(config_map_data, indent=2)

    logger.debug(
        "Adding host path volume for local path `%s` to kubeflow pipeline"
        "viewer pod template configuration.",
        local_path,
    )
    subprocess.check_call(
        [
            "kubectl",
            "--context",
            kubernetes_context,
            "-n",
            "kubeflow",
            "patch",
            "configmap/ml-pipeline-ui-configmap",
            "--type",
            "merge",
            "-p",
            config_map_data_json,
        ]
    )

    deployment_patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "ml-pipeline-ui",
                            "volumeMounts": [
                                {
                                    "mountPath": local_path,
                                    "name": "local-artifact-store",
                                }
                            ],
                        }
                    ],
                    "volumes": [
                        {
                            "hostPath": {
                                "path": local_path,
                                "type": "Directory",
                            },
                            "name": "local-artifact-store",
                        }
                    ],
                }
            }
        }
    }
    deployment_patch_json = json.dumps(deployment_patch, indent=2)

    logger.debug(
        "Adding host path volume for local path `%s` to the kubeflow UI",
        local_path,
    )
    subprocess.check_call(
        [
            "kubectl",
            "--context",
            kubernetes_context,
            "-n",
            "kubeflow",
            "patch",
            "deployment/ml-pipeline-ui",
            "--type",
            "strategic",
            "-p",
            deployment_patch_json,
        ]
    )
    wait_until_kubeflow_pipelines_ready(kubernetes_context=kubernetes_context)

    logger.info("Finished patching Kubeflow Pipelines setup.")


def start_kfp_ui_daemon(
    pid_file_path: str,
    log_file_path: str,
    port: int,
    kubernetes_context: str,
) -> None:
    """Starts a daemon process that forwards ports.

    This is so the Kubeflow Pipelines UI is accessible in the browser.

    Args:
        pid_file_path: Path where the file with the daemons process ID should
            be written.
        log_file_path: Path to a file where the daemon logs should be written.
        port: Port on which the UI should be accessible.
        kubernetes_context: The kubernetes context for the cluster where
            Kubeflow Pipelines is running.
    """
    command = [
        "kubectl",
        "--context",
        kubernetes_context,
        "--namespace",
        "kubeflow",
        "port-forward",
        "svc/ml-pipeline-ui",
        f"{port}:80",
    ]

    if not networking_utils.port_available(port):
        modified_command = command.copy()
        modified_command[-1] = "PORT:80"
        logger.warning(
            "Unable to port-forward Kubeflow Pipelines UI to local port %d "
            "because the port is occupied. In order to access the Kubeflow "
            "Pipelines UI at http://localhost:PORT/, please run '%s' in a "
            "separate command line shell (replace PORT with a free port of "
            "your choice).",
            port,
            " ".join(modified_command),
        )
    elif sys.platform == "win32":
        logger.warning(
            "Daemon functionality not supported on Windows. "
            "In order to access the Kubeflow Pipelines UI at "
            "http://localhost:%d/, please run '%s' in a separate command "
            "line shell.",
            port,
            " ".join(command),
        )
    else:
        from zenml.utils import daemon

        def _daemon_function() -> None:
            """Port-forwards the Kubeflow Pipelines UI pod."""
            subprocess.check_call(command)

        daemon.run_as_daemon(
            _daemon_function, pid_file=pid_file_path, log_file=log_file_path
        )
        logger.info(
            "Started Kubeflow Pipelines UI daemon (check the daemon logs at %s "
            "in case you're not able to view the UI). The Kubeflow Pipelines "
            "UI should now be accessible at http://localhost:%d/.",
            log_file_path,
            port,
        )


def stop_kfp_ui_daemon(pid_file_path: str) -> None:
    """Stops the KFP UI daemon process if it is running.

    Args:
        pid_file_path: Path to the file with the daemons process ID.
    """
    if fileio.exists(pid_file_path):
        if sys.platform == "win32":
            # Daemon functionality is not supported on Windows, so the PID
            # file won't exist. This if clause exists just for mypy to not
            # complain about missing functions
            pass
        else:
            from zenml.utils import daemon

            daemon.stop_daemon(pid_file_path)
            fileio.remove(pid_file_path)
            logger.info("Stopped Kubeflow Pipelines UI daemon.")
