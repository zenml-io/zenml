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
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type, cast

import distro

from zenml import __version__
from zenml.logger import get_logger
from zenml.utils.singleton import SingletonMetaClass

if TYPE_CHECKING:
    from zenml.steps import StepEnvironment

logger = get_logger(__name__)


def get_environment() -> str:
    """Returns a string representing the execution environment of the pipeline.
    Currently, one of `docker`, `paperspace`, 'colab', or `native`"""
    if Environment.in_docker():
        return "docker"
    elif Environment.in_google_colab():
        return "colab"
    elif Environment.in_paperspace_gradient():
        return "paperspace"
    elif Environment.in_notebook():
        return "notebook"
    else:
        return "native"


def get_system_details() -> str:
    """Returns OS, python and ZenML information."""
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
        """Returns if a step is currently running."""
        from zenml.steps import STEP_ENVIRONMENT_NAME

        # A step is considered to be running if there is an active step
        # environment
        return self.has_component(STEP_ENVIRONMENT_NAME)

    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Information about the operating system."""
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
        """If the current python process is running in a docker container."""
        # TODO [ENG-167]: Make this more reliable and add test.
        try:
            with open("/proc/1/cgroup", "rt") as ifh:
                info = ifh.read()
                return "docker" in info or "kubepod" in info
        except (FileNotFoundError, Exception):
            return False

    @staticmethod
    def in_google_colab() -> bool:
        """If the current Python process is running in a Google Colab."""
        try:
            import google.colab  # noqa

            return True

        except ModuleNotFoundError:
            return False

    @staticmethod
    def in_notebook() -> bool:
        """If the current Python process is running in a notebook."""
        if find_spec("IPython") is not None:
            from IPython import get_ipython  # type: ignore

            if get_ipython().__class__.__name__ in [
                "TerminalInteractiveShell",
                "ZMQInteractiveShell",
            ]:
                return True
        return False

    @staticmethod
    def in_paperspace_gradient() -> bool:
        """If the current Python process is running in Paperspace Gradient."""
        return "PAPERSPACE_NOTEBOOK_REPO_ID" in os.environ

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
            logger.debug(f"Deregistered environment component {component.NAME}")

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
        """Get all registered environment components."""
        return self._components.copy()

    def has_component(self, name: str) -> bool:
        """Check if the environment component with a known name is currently
        available.

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
    """Metaclass responsible for registering different EnvironmentComponent
    instances in the global Environment"""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "EnvironmentComponentMeta":
        """Hook into creation of an BaseEnvironmentComponent class."""
        cls = cast(
            Type["BaseEnvironmentComponent"],
            super().__new__(mcs, name, bases, dct),
        )
        if name != "BaseEnvironmentComponent":
            assert (
                cls.NAME and cls.NAME != _BASE_ENVIRONMENT_COMPONENT_NAME
            ), "You should specify a unique NAME when creating an EnvironmentComponent !"
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
        """Activate the environment component and register it in the global
        Environment.

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
        """Deactivate the environment component and deregister it from the
        global Environment.

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
        """Check if the environment component is currently active."""
        return self._active

    def __enter__(self) -> "BaseEnvironmentComponent":
        """Environment component context entry point.

        Returns:
            The BaseEnvironmentComponent instance.
        """
        self.activate()
        return self

    def __exit__(self, *args: Any) -> None:
        """Environment component context exit point."""
        self.deactivate()
