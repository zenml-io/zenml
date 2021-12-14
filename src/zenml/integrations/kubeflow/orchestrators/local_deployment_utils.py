import json
import shutil
import subprocess
import sys
import time

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import yaml_utils

KFP_VERSION = "1.7.1"
logger = get_logger(__name__)


def check_prerequisites() -> bool:
    """Checks whether all prerequisites for a local kubeflow pipelines
    deployment are installed."""
    k3d_installed = shutil.which("k3d") is not None
    kubectl_installed = shutil.which("kubectl") is not None
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
    """Checks whether there exists a K3D cluster with the given name."""
    output = subprocess.check_output(
        ["k3d", "cluster", "list", "--output", "json"]
    )
    clusters = json.loads(output)
    for cluster in clusters:
        if cluster["name"] == cluster_name:
            return True
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
    config_dir_path = fileio.get_zenml_config_dir()
    subprocess.check_call(
        [
            "k3d",
            "cluster",
            "create",
            cluster_name,
            "--registry-create",
            registry_name,
            "--registry-config",
            registry_config_path,
            "--volume",
            f"{config_dir_path}:{config_dir_path}",
        ]
    )
    logger.info("Finished K3D cluster creation.")


def delete_k3d_cluster(cluster_name: str) -> None:
    """Deletes a K3D cluster with the given name."""
    subprocess.check_call(["k3d", "cluster", "delete", cluster_name])
    logger.info("Deleted local k3d cluster '%s'.", cluster_name)


def kubeflow_pipelines_ready(kubernetes_context: str) -> bool:
    """Returns whether all Kubeflow Pipelines pods are ready.

    Args:
        kubernetes_context: The kubernetes context in which the pods
            should be checked.
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
                "--all",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


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
            f"github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref={KFP_VERSION}",
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
            f"github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic-pns?ref={KFP_VERSION}",
        ]
    )

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

        logger.info("One or more pods not ready yet, waiting for 30 seconds...")
        time.sleep(30)

    logger.info("Finished Kubeflow Pipelines setup.")


def start_kfp_ui_daemon(pid_file_path: str, port: int) -> None:
    """Starts a daemon process that forwards ports so the Kubeflow Pipelines
    UI is accessible in the browser.

    Args:
        pid_file_path: Path where the file with the daemons process ID should
            be written.
        port: Port on which the UI should be accessible.
    """

    def _daemon_function() -> None:
        """Port-forwards the Kubeflow Pipelines UI pod."""
        subprocess.check_call(
            [
                "kubectl",
                "--namespace",
                "kubeflow",
                "port-forward",
                "svc/ml-pipeline-ui",
                f"{port}:80",
            ]
        )

    from zenml.utils import daemon

    # TODO [ENG-234]: Update with smarter solution for windows daemon
    if sys.platform == "win32":
        pass
    else:
        daemon.run_as_daemon(
            _daemon_function,
            pid_file=pid_file_path,
        )
        logger.info("Started Kubeflow Pipelines UI daemon.")
