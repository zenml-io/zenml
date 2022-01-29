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
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

import distro

from zenml.utils.singleton import SingletonMetaClass


class Environment(metaclass=SingletonMetaClass):
    """Provides environment information."""

    def __init__(self) -> None:
        """Initializes an Environment instance.

        Note: Environment is a singleton, which means this method will only
        get called once. All following `Environment()` calls will return the
        already existing instance.
        """
        self.__currently_running_step = False

    @property
    def currently_running_step(self) -> bool:
        """Returns if a step is currently running."""
        return self.__currently_running_step

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
        """If the current python process is running in a Google Colab."""
        return "COLAB_GPU" in os.environ

    @staticmethod
    def in_jupyter_notebook() -> bool:
        """If the current python process is running in a Jupyter notebook."""
        try:
            from IPython import get_ipython  # type: ignore

            if get_ipython() is None:
                # IPython is installed but not running from a notebook
                return False
            else:
                return True
        except ImportError:
            # We do not even have IPython installed
            return False

    @staticmethod
    def in_paperspace_gradient() -> bool:
        """Returns: True if running in a Paperspace Gradient env, else False"""
        if "PAPERSPACE_NOTEBOOK_REPO_ID" in os.environ:
            return True
        return False

    @contextmanager
    def _set_attributes(
        self, currently_running_step: Optional[bool] = None
    ) -> Iterator["Environment"]:
        """Sets attributes on the singleton instance.

        These attributes will only be persisted for the active duration of this
        contextmanager:
        ```python
        env = Environment()
        print(env.currently_running_step)  # False

        with Environment()._set_attributes(currently_running_step=True):
            print(env.currently_running_step)  # True

        print(env.currently_running_step)  # False
        ```

        Calls to this contextmanager can also be nested:
        ```python
        with Environment()._set_attributes(...):
            # only attributes from outer context manager are set
            with Environment()._set_attributes(...):
                # attributes from outer and inner context manager are set
                # (inner context manager can overwrite values from outer one)

            # only attributes from outer context manager are set
        ```
        """
        old_dict = self.__dict__.copy()

        if currently_running_step is not None:
            self.__currently_running_step = currently_running_step

        try:
            yield self
        finally:
            self.__dict__ = old_dict
