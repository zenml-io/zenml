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
import os
import platform
from typing import Any, Dict

import distro


class Environment:
    """Provides environment information."""

    __currently_running_step = False

    @classmethod
    def currently_running_step(cls) -> bool:
        """Returns if a step is currently running."""
        return cls.__currently_running_step

    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Returns system info as a dict.

        Returns:
            A dict of system information.
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
        """Returns the python version of the running interpreter."""
        return platform.python_version()

    @staticmethod
    def in_docker() -> bool:
        """Returns: True if running in a Docker container, else False"""
        # TODO [ENG-167]: Make this more reliable and add test.
        try:
            with open("/proc/1/cgroup", "rt") as ifh:
                info = ifh.read()
                return "docker" in info or "kubepod" in info
        except (FileNotFoundError, Exception):
            return False

    @staticmethod
    def in_google_colab() -> bool:
        """Returns: True if running in a Google Colab env, else False"""
        if "COLAB_GPU" in os.environ:
            return True
        return False

    @staticmethod
    def in_paperspace_gradient() -> bool:
        """Returns: True if running in a Paperspace Gradient env, else False"""
        if "PAPERSPACE_NOTEBOOK_REPO_ID" in os.environ:
            return True
        return False
