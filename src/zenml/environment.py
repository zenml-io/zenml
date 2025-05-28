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
"""Environment implementation."""

import os
import platform
import subprocess
from typing import Any, Dict, List

import distro

from zenml.constants import INSIDE_ZENML_CONTAINER
from zenml.enums import EnvironmentType
from zenml.logger import get_logger
from zenml.utils.singleton import SingletonMetaClass

logger = get_logger(__name__)


def get_run_environment_dict() -> Dict[str, Any]:
    """Returns a dictionary of the current run environment.

    Everything that is returned here will be saved in the DB as
    `pipeline_run.client_environment` and
    `pipeline_run.orchestrator_environment` for client and orchestrator
    respectively.

    Returns:
        A dictionary of the current run environment.
    """
    env_dict: Dict[str, Any] = {
        "environment": str(get_environment()),
        **Environment.get_system_info(),
        "python_version": Environment.python_version(),
    }

    try:
        python_packages = Environment.get_python_packages()
    except RuntimeError:
        logger.warning("Failed to get list of installed Python packages")
    else:
        # TODO: We send the python packages as a string right now to keep
        # backwards compatibility with old versions. We should update this to
        # be a list of strings eventually.
        env_dict["python_packages"] = "\n".join(python_packages)

    return env_dict


def get_environment() -> str:
    """Returns a string representing the execution environment of the pipeline.

    Returns:
        str: the execution environment
    """
    # Order is important here
    if Environment.in_kubernetes():
        return EnvironmentType.KUBERNETES
    elif Environment.in_github_actions():
        return EnvironmentType.GITHUB_ACTION
    elif Environment.in_gitlab_ci():
        return EnvironmentType.GITLAB_CI
    elif Environment.in_circle_ci():
        return EnvironmentType.CIRCLE_CI
    elif Environment.in_bitbucket_ci():
        return EnvironmentType.BITBUCKET_CI
    elif Environment.in_ci():
        return EnvironmentType.GENERIC_CI
    elif Environment.in_github_codespaces():
        return EnvironmentType.GITHUB_CODESPACES
    elif Environment.in_zenml_codespace():
        return EnvironmentType.ZENML_CODESPACE
    elif Environment.in_vscode_remote_container():
        return EnvironmentType.VSCODE_REMOTE_CONTAINER
    elif Environment.in_lightning_ai_studio():
        return EnvironmentType.LIGHTNING_AI_STUDIO
    elif Environment.in_docker():
        return EnvironmentType.DOCKER
    elif Environment.in_container():
        return EnvironmentType.CONTAINER
    elif Environment.in_google_colab():
        return EnvironmentType.COLAB
    elif Environment.in_paperspace_gradient():
        return EnvironmentType.PAPERSPACE
    elif Environment.in_notebook():
        return EnvironmentType.NOTEBOOK
    elif Environment.in_wsl():
        return EnvironmentType.WSL
    else:
        return EnvironmentType.NATIVE


class Environment(metaclass=SingletonMetaClass):
    """Provides environment information."""

    def __init__(self) -> None:
        """Initializes an Environment instance.

        Note: Environment is a singleton class, which means this method will
        only get called once. All following `Environment()` calls will return
        the previously initialized instance.
        """

    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """Information about the operating system.

        Returns:
            A dictionary containing information about the operating system.
        """
        system = platform.system()

        if system == "Windows":
            release, version, csd, ptype = platform.win32_ver()

            return {
                "os": "windows",
                "windows_version_release": release,
                "windows_version": version,
                "windows_version_service_pack": csd,
                "windows_version_os_type": ptype,
            }

        if system == "Darwin":
            return {"os": "mac", "mac_version": platform.mac_ver()[0]}

        if system == "Linux":
            return {
                "os": "linux",
                "linux_distro": distro.id(),
                "linux_distro_like": distro.like(),
                "linux_distro_version": distro.version(),
            }

        # We don't collect data for any other system.
        return {"os": "unknown"}

    @staticmethod
    def python_version() -> str:
        """Returns the python version of the running interpreter.

        Returns:
            str: the python version
        """
        return platform.python_version()

    @staticmethod
    def in_container() -> bool:
        """If the current python process is running in a container.

        Returns:
            `True` if the current python process is running in a
            container, `False` otherwise.
        """
        # TODO [ENG-167]: Make this more reliable and add test.
        return INSIDE_ZENML_CONTAINER

    @staticmethod
    def in_docker() -> bool:
        """If the current python process is running in a docker container.

        Returns:
            `True` if the current python process is running in a docker
            container, `False` otherwise.
        """
        if os.path.exists("./dockerenv") or os.path.exists("/.dockerinit"):
            return True

        try:
            with open("/proc/1/cgroup", "rt") as ifh:
                info = ifh.read()
                return "docker" in info
        except (FileNotFoundError, Exception):
            return False

    @staticmethod
    def in_kubernetes() -> bool:
        """If the current python process is running in a kubernetes pod.

        Returns:
            `True` if the current python process is running in a kubernetes
            pod, `False` otherwise.
        """
        if "KUBERNETES_SERVICE_HOST" in os.environ:
            return True

        try:
            with open("/proc/1/cgroup", "rt") as ifh:
                info = ifh.read()
                return "kubepod" in info
        except (FileNotFoundError, Exception):
            return False

    @staticmethod
    def in_google_colab() -> bool:
        """If the current Python process is running in a Google Colab.

        Returns:
            `True` if the current Python process is running in a Google Colab,
            `False` otherwise.
        """
        try:
            import google.colab  # noqa

            return True

        except ModuleNotFoundError:
            return False

    @staticmethod
    def in_notebook() -> bool:
        """If the current Python process is running in a notebook.

        Returns:
            `True` if the current Python process is running in a notebook,
            `False` otherwise.
        """
        if Environment.in_google_colab():
            return True

        try:
            ipython = get_ipython()  # type: ignore[name-defined]
        except NameError:
            return False

        if ipython.__class__.__name__ in [
            "TerminalInteractiveShell",
            "ZMQInteractiveShell",
            "DatabricksShell",
        ]:
            return True
        return False

    @staticmethod
    def in_github_codespaces() -> bool:
        """If the current Python process is running in GitHub Codespaces.

        Returns:
            `True` if the current Python process is running in GitHub Codespaces,
            `False` otherwise.
        """
        return (
            "CODESPACES" in os.environ
            or "GITHUB_CODESPACE_TOKEN" in os.environ
            or "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN" in os.environ
        )

    @staticmethod
    def in_zenml_codespace() -> bool:
        """If the current Python process is running in ZenML Codespaces.

        Returns:
            `True` if the current Python process is running in ZenML Codespaces,
            `False` otherwise.
        """
        return os.environ.get("ZENML_ENVIRONMENT") == "codespace"

    @staticmethod
    def in_vscode_remote_container() -> bool:
        """If the current Python process is running in a VS Code Remote Container.

        Returns:
            `True` if the current Python process is running in a VS Code Remote Container,
            `False` otherwise.
        """
        return (
            "REMOTE_CONTAINERS" in os.environ
            or "VSCODE_REMOTE_CONTAINERS_SESSION" in os.environ
        )

    @staticmethod
    def in_paperspace_gradient() -> bool:
        """If the current Python process is running in Paperspace Gradient.

        Returns:
            `True` if the current Python process is running in Paperspace
            Gradient, `False` otherwise.
        """
        return "PAPERSPACE_NOTEBOOK_REPO_ID" in os.environ

    @staticmethod
    def in_github_actions() -> bool:
        """If the current Python process is running in GitHub Actions.

        Returns:
            `True` if the current Python process is running in GitHub
            Actions, `False` otherwise.
        """
        return "GITHUB_ACTIONS" in os.environ

    @staticmethod
    def in_gitlab_ci() -> bool:
        """If the current Python process is running in GitLab CI.

        Returns:
            `True` if the current Python process is running in GitLab
            CI, `False` otherwise.
        """
        return "GITLAB_CI" in os.environ

    @staticmethod
    def in_circle_ci() -> bool:
        """If the current Python process is running in Circle CI.

        Returns:
            `True` if the current Python process is running in Circle
            CI, `False` otherwise.
        """
        return "CIRCLECI" in os.environ

    @staticmethod
    def in_bitbucket_ci() -> bool:
        """If the current Python process is running in Bitbucket CI.

        Returns:
            `True` if the current Python process is running in Bitbucket
            CI, `False` otherwise.
        """
        return "BITBUCKET_BUILD_NUMBER" in os.environ

    @staticmethod
    def in_ci() -> bool:
        """If the current Python process is running in any CI.

        Returns:
            `True` if the current Python process is running in any
            CI, `False` otherwise.
        """
        return "CI" in os.environ

    @staticmethod
    def in_wsl() -> bool:
        """If the current process is running in Windows Subsystem for Linux.

        source: https://www.scivision.dev/python-detect-wsl/

        Returns:
            `True` if the current process is running in WSL, `False` otherwise.
        """
        return "microsoft-standard" in platform.uname().release

    @staticmethod
    def in_lightning_ai_studio() -> bool:
        """If the current Python process is running in Lightning.ai studios.

        Returns:
            `True` if the current Python process is running in Lightning.ai studios,
            `False` otherwise.
        """
        return (
            "LIGHTNING_CLOUD_URL" in os.environ
            and "LIGHTNING_CLOUDSPACE_HOST" in os.environ
        )

    @staticmethod
    def get_python_packages() -> List[str]:
        """Returns a list of installed Python packages.

        Raises:
            RuntimeError: If the process to get the list of installed packages
                fails.

        Returns:
            List of installed packages in pip freeze format.
        """
        try:
            output = subprocess.check_output(["pip", "freeze"]).decode()
            return output.strip().split("\n")
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "Failed to get list of installed Python packages"
            )
