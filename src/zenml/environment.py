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
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type, cast

import distro

from zenml import __version__
from zenml.constants import INSIDE_ZENML_CONTAINER
from zenml.enums import EnvironmentType
from zenml.logger import get_logger
from zenml.utils.singleton import SingletonMetaClass

if TYPE_CHECKING:
    from zenml.steps import StepEnvironment

logger = get_logger(__name__)


def get_run_environment_dict() -> Dict[str, str]:
    """Returns a dictionary of the current run environment.

    Everything that is returned here will be saved in the DB as
    `pipeline_run.client_environment` and
    `pipeline_run.orchestrator_environment` for client and orchestrator
    respectively.

    Returns:
        A dictionary of the current run environment.
    """
    return {
        "environment": get_environment(),
        **Environment.get_system_info(),
        "python_version": Environment.python_version(),
    }


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


def get_system_details() -> str:
    """Returns OS, python and ZenML information.

    Returns:
        str: OS, python and ZenML information
    """
    from zenml.integrations.registry import integration_registry

    info = {
        "ZenML version": __version__,
        "Install path": Path(__file__).resolve().parent,
        "Python version": Environment.python_version(),
        "Platform information": Environment.get_system_info(),
        "Environment": get_environment(),
        "Integrations": integration_registry.get_installed_integrations(),
    }
    return "\n".join(
        "{:>10} {}".format(k + ":", str(v).replace("\n", " "))
        for k, v in info.items()
    )


class Environment(metaclass=SingletonMetaClass):
    """Provides environment information.

    Individual environment components can be registered separately to extend
    the global Environment object with additional information (see
    `BaseEnvironmentComponent`).
    """

    def __init__(self) -> None:
        """Initializes an Environment instance.

        Note: Environment is a singleton class, which means this method will
        only get called once. All following `Environment()` calls will return
        the previously initialized instance.
        """
        self._components: Dict[str, "BaseEnvironmentComponent"] = {}

    @property
    def step_is_running(self) -> bool:
        """Returns if a step is currently running.

        Returns:
            `True` if a step is currently running, `False` otherwise.
        """
        from zenml.steps import STEP_ENVIRONMENT_NAME

        logger.warning(
            "`Environment().step_is_running` is deprecated and will be "
            "removed in a future release."
        )
        return self.has_component(STEP_ENVIRONMENT_NAME)

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

    def register_component(
        self, component: "BaseEnvironmentComponent"
    ) -> "BaseEnvironmentComponent":
        """Registers an environment component.

        Args:
            component: a BaseEnvironmentComponent instance.

        Returns:
            The newly registered environment component, or the environment
            component that was already registered under the given name.
        """
        if component.NAME not in self._components:
            self._components[component.NAME] = component
            logger.debug(f"Registered environment component {component.NAME}")
            return component
        else:
            logger.warning(
                f"Ignoring attempt to overwrite an existing Environment "
                f"component registered under the name {component.NAME}."
            )
            return self._components[component.NAME]

    def deregister_component(
        self, component: "BaseEnvironmentComponent"
    ) -> None:
        """Deregisters an environment component.

        Args:
            component: a BaseEnvironmentComponent instance.
        """
        if self._components.get(component.NAME) is component:
            del self._components[component.NAME]
            logger.debug(
                f"Deregistered environment component {component.NAME}"
            )

        else:
            logger.warning(
                f"Ignoring attempt to deregister an inexistent Environment "
                f"component with the name {component.NAME}."
            )

    def get_component(self, name: str) -> Optional["BaseEnvironmentComponent"]:
        """Get the environment component with a known name.

        Args:
            name: the environment component name.

        Returns:
            The environment component that is registered under the given name,
            or None if no such component is registered.
        """
        return self._components.get(name)

    def get_components(
        self,
    ) -> Dict[str, "BaseEnvironmentComponent"]:
        """Get all registered environment components.

        Returns:
            A dictionary containing all registered environment components.
        """
        return self._components.copy()

    def has_component(self, name: str) -> bool:
        """Check if the environment component with a known name is available.

        Args:
            name: the environment component name.

        Returns:
            `True` if an environment component with the given name is
            currently registered for the given name, `False` otherwise.
        """
        return name in self._components

    def __getitem__(self, name: str) -> "BaseEnvironmentComponent":
        """Get the environment component with the given name.

        Args:
            name: the environment component name.

        Returns:
            `BaseEnvironmentComponent` instance that was registered for the
            given name.

        Raises:
            KeyError: if no environment component is registered for the given
                name.
        """
        from zenml.steps import STEP_ENVIRONMENT_NAME

        if name == STEP_ENVIRONMENT_NAME:
            logger.warning(
                "The `StepEnvironment` class and corresponding "
                "`Environment.step_environment` property are deprecated and "
                "will be removed in a future release. Please use the "
                " `StepContext` to access information about the current run "
                "instead, as shown here: "
                "https://docs.zenml.io/how-to/track-metrics-metadata/fetch-metadata-within-steps"
            )
        if name in self._components:
            return self._components[name]
        else:
            raise KeyError(
                f"No environment component with name {name} is currently "
                f"registered. This could happen for example if you're trying "
                f"to access an environment component that is only available "
                f"in the context of a step function, or, in the case of "
                f"globally available environment components, if a relevant "
                f"integration has not been activated yet."
            )

    @property
    def step_environment(self) -> "StepEnvironment":
        """Get the current step environment component, if one is available.

        This should only be called in the context of a step function.

        Returns:
            The `StepEnvironment` that describes the current step.
        """
        from zenml.steps import STEP_ENVIRONMENT_NAME, StepEnvironment

        return cast(StepEnvironment, self[STEP_ENVIRONMENT_NAME])


_BASE_ENVIRONMENT_COMPONENT_NAME = "base_environment_component"


class EnvironmentComponentMeta(type):
    """Metaclass registering environment components in the global Environment."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "EnvironmentComponentMeta":
        """Hook into creation of an BaseEnvironmentComponent class.

        Args:
            name: the name of the class being created.
            bases: the base classes of the class being created.
            dct: the dictionary of attributes of the class being created.

        Returns:
            The newly created class.
        """
        cls = cast(
            Type["BaseEnvironmentComponent"],
            super().__new__(mcs, name, bases, dct),
        )
        if name != "BaseEnvironmentComponent":
            assert cls.NAME and cls.NAME != _BASE_ENVIRONMENT_COMPONENT_NAME, (
                "You should specify a unique NAME when creating an "
                "EnvironmentComponent!"
            )
        return cls


class BaseEnvironmentComponent(metaclass=EnvironmentComponentMeta):
    """Base Environment component class.

    All Environment components must inherit from this class and provide a unique
    value for the `NAME` attribute.


    Different code components can independently contribute with information to
    the global Environment by extending and instantiating this class:

    ```python
    from zenml.environment import BaseEnvironmentComponent

    MY_ENV_NAME = "my_env"

    class MyEnvironmentComponent(BaseEnvironmentComponent):

        NAME = MY_ENV_NAME

        def __init__(self, my_env_attr: str) -> None:
            super().__init__()
            self._my_env_attr = my_env_attr

        @property
        def my_env_attr(self) -> str:
            return self._my_env_attr

    my_env = MyEnvironmentComponent()
    ```


    There are two ways to register and deregister a `BaseEnvironmentComponent`
    instance with the global Environment:

    1. by explicitly calling its `activate` and `deactivate` methods:

    ```python
    my_env.activate()

    # ... environment component is active
    # and registered in the global Environment

    my_env.deactivate()

    # ... environment component is not active
    ```

    2. by using the instance as a context:

    ```python
    with my_env:
        # ... environment component is active
        # and registered in the global Environment

    # ... environment component is not active
    ```

    While active, environment components can be discovered and accessed from
    the global environment:

    ```python
    from foo.bar.my_env import MY_ENV_NAME
    from zenml.environment import Environment

    my_env = Environment.get_component(MY_ENV_NAME)

    # this works too, but throws an error if the component is not active:

    my_env = Environment[MY_ENV_NAME]
    ```

    Attributes:
        NAME: a unique name for this component. This name will be used to
            register this component in the global Environment and to
            subsequently retrieve it by calling `Environment().get_component`.
    """

    NAME: str = _BASE_ENVIRONMENT_COMPONENT_NAME

    def __init__(self) -> None:
        """Initialize an environment component."""
        self._active = False

    def activate(self) -> None:
        """Activate the environment component and register it in the global Environment.

        Raises:
            RuntimeError: if the component is already active.
        """
        if self._active:
            raise RuntimeError(
                f"Environment component {self.NAME} is already active."
            )
        Environment().register_component(self)
        self._active = True

    def deactivate(self) -> None:
        """Deactivate the environment component and deregister it from the global Environment.

        Raises:
            RuntimeError: if the component is not active.
        """
        if not self._active:
            raise RuntimeError(
                f"Environment component {self.NAME} is not active."
            )
        Environment().deregister_component(self)
        self._active = False

    @property
    def active(self) -> bool:
        """Check if the environment component is currently active.

        Returns:
            `True` if the environment component is currently active, `False`
            otherwise.
        """
        return self._active

    def __enter__(self) -> "BaseEnvironmentComponent":
        """Environment component context entry point.

        Returns:
            The BaseEnvironmentComponent instance.
        """
        self.activate()
        return self

    def __exit__(self, *args: Any) -> None:
        """Environment component context exit point.

        Args:
            *args: the arguments passed to the context exit point.
        """
        self.deactivate()
