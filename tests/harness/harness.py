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
"""ZenML test harness."""

import logging
from abc import ABCMeta
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Generator, List, Optional, Tuple, cast

import yaml
from pydantic import ValidationError

from tests.harness.deployment.base import BaseTestDeployment
from tests.harness.environment import TestEnvironment
from tests.harness.model import (
    Configuration,
    DeploymentConfig,
    EnvironmentConfig,
    Secret,
    TestConfig,
    TestRequirements,
)

if TYPE_CHECKING:
    from zenml.client import Client
    from zenml.stack import Stack

DEFAULT_CONFIG_PATH = str(Path(__file__).parent / "cfg")
DEFAULT_DEPLOYMENT_NAME = "default"


class TestHarnessMetaClass(ABCMeta):
    """Test harness singleton metaclass.

    This metaclass is used to enforce a singleton instance of the TestHarness
    class.
    """

    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        """Initialize the TestHarness class.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.
        """
        super().__init__(*args, **kwargs)
        cls._harness: Optional["TestHarness"] = None

    def __call__(cls, *args: Any, **kwargs: Any) -> "TestHarness":
        """Create or return the TestHarness singleton.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            The TestHarness singleton.
        """
        if not cls._harness:
            cls._harness = cast(
                "TestHarness", super().__call__(*args, **kwargs)
            )
            cls._harness.compile()

        return cls._harness


class TestHarness(metaclass=TestHarnessMetaClass):
    """ZenML test harness singleton."""

    def __init__(
        self,
        config_path: str = DEFAULT_CONFIG_PATH,
    ) -> None:
        """Initialize the TestHarness singleton.

        Args:
            config_path: Path to directory with configuration files.
        """
        self.config = self.load_config(config_path)
        self._active_environment: Optional[TestEnvironment] = None

    def set_environment(
        self,
        environment_name: Optional[str] = None,
        deployment_name: Optional[str] = None,
        requirements_names: List[str] = [],
    ) -> TestEnvironment:
        """Sets the active environment.

        Args:
            environment_name: Name of the environment to use. If not specified,
                an environment will be created automatically from the supplied
                (or default) deployment and the supplied requirements
                (if any).
            deployment_name: Name of the deployment to use. Ignored if an
                environment name is specified.
            requirements_names: List of global test requirements names to use.
                Ignored if an environment name is specified.

        Returns:
            The active environment.

        Raises:
            ValueError: If the specified environment does not exist.
        """
        if environment_name is not None:
            environment_cfg = self.get_environment_config(environment_name)
            if environment_cfg is None:
                raise ValueError(
                    f"Environment '{environment_name}' does not exist."
                )
        else:
            # If no environment is specified, create an ad-hoc environment
            # consisting of the supplied deployment (or the default one) and
            # the supplied test requirements (if present).
            deployment_name = deployment_name or DEFAULT_DEPLOYMENT_NAME

            # Create a temporary environment for the test
            environment_cfg = EnvironmentConfig(
                name=f"{deployment_name}-ad-hoc",
                deployment=deployment_name,
                requirements=requirements_names,
            )
            environment_cfg.compile(self)

        self._active_environment = environment_cfg.get_environment()
        return self._active_environment

    @property
    def active_environment(self) -> TestEnvironment:
        """Returns the active environment.

        Returns:
            The active environment.
        """
        if self._active_environment is None:
            # If no environment is set, use an ad-hoc environment consisting
            # of the default deployment and no requirements.
            self.set_environment()
        assert self._active_environment is not None
        return self._active_environment

    @property
    def active_deployment(self) -> BaseTestDeployment:
        """Returns the active deployment.

        Returns:
            The active deployment.
        """
        return self.active_environment.deployment

    def load_config(
        self, config_path: str = DEFAULT_CONFIG_PATH
    ) -> Configuration:
        """Loads the configuration from a file path.

        Args:
            config_path: Path to directory with configuration files.

        Returns:
            The loaded configuration.

        Raises:
            ValueError: If a configuration file is invalid.
        """
        config = Configuration(config_file=config_path)  # type: ignore[call-arg]
        for config_file in Path(config_path).glob("**/*.yaml"):
            with open(config_file, "r") as f:
                try:
                    config_values = yaml.safe_load(f.read())
                    if config_values is None:
                        continue
                    partial_config = Configuration(  # type: ignore[call-arg]
                        config_file=str(config_file), **config_values
                    )
                except ValidationError as e:
                    raise ValueError(
                        f"Validation error in configuration file "
                        f"'{config_file}': {e}"
                    )
                config.merge(partial_config)

        return config

    def compile(self) -> None:
        """Compiles the configuration.

        Raises:
            ValueError: If the configuration is invalid.
        """
        self.deployment_configs = {d.name: d for d in self.config.deployments}
        self.secrets = {s.name: s for s in self.config.secrets}
        self.tests = {t.module: t for t in self.config.tests}
        self.requirements = {c.name: c for c in self.config.requirements}
        self.environment_configs = {
            e.name: e for e in self.config.environments
        }

        try:
            self.config.compile(self)
        except ValueError as e:
            raise ValueError(f"Configuration validation error: {e}") from e

        self.deployments = {
            d.name: d.get_deployment() for d in self.config.deployments
        }
        self.environments = {
            e.name: e.get_environment() for e in self.config.environments
        }

    def get_deployment_config(self, name: str) -> Optional[DeploymentConfig]:
        """Returns a deployment configuration by name.

        Args:
            name: Name of the deployment.

        Returns:
            A deployment configuration, or None if no deployment with the given
            name was found.
        """
        return self.deployment_configs.get(name)

    def get_deployment(self, name: str) -> BaseTestDeployment:
        """Returns a deployment instance by name.

        Args:
            name: Name of the deployment.

        Returns:
            The deployment.

        Raises:
            KeyError: If no deployment with the given name exists.
        """
        if name not in self.deployments:
            raise KeyError(f"Deployment with name '{name}' does not exist.")
        return self.deployments[name]

    def get_secret(self, name: str) -> Optional[Secret]:
        """Returns a secret by name.

        Args:
            name: Name of the secret.

        Returns:
            A secret or None if no secret with the given name exists.
        """
        return self.secrets.get(name)

    def get_environment_config(self, name: str) -> Optional[EnvironmentConfig]:
        """Returns an environment configuration by name.

        Args:
            name: Name of the environment.

        Returns:
            An environment instance or None if no environment with the
            given name exists.
        """
        return self.environment_configs.get(name)

    def get_environment(self, name: str) -> TestEnvironment:
        """Returns an environment instance by name.

        Args:
            name: Name of the environment.

        Returns:
            An environment instance.

        Raises:
            KeyError: If no environment with the given name exists.
        """
        if name not in self.environments:
            raise KeyError(f"Environment with name '{name}' does not exist.")
        return self.environments[name]

    def get_global_requirements(self, name: str) -> Optional[TestRequirements]:
        """Returns a global requirements configuration by name.

        Args:
            name: Name of the global requirements configuration.

        Returns:
            A global global requirements configuration or None if no entry
            with the given name exists.
        """
        return self.requirements.get(name)

    def get_test_requirements(
        self, module: ModuleType
    ) -> Optional[TestConfig]:
        """Returns a test requirements configuration associated with a pytest test module.

        Args:
            module: A pytest test module.

        Returns:
            A test requirements configuration or None if no such configuration
            was found for the given module.
        """
        if module.__name__ in self.tests:
            return self.tests[module.__name__]
        elif module.__package__ in self.tests:
            return self.tests[module.__package__]

        return None

    def _get_test_module_requirements(
        self,
        module: ModuleType,
    ) -> Optional[TestConfig]:
        """Returns the test requirements for a given test module.

        Args:
            module: A pytest test module.

        Returns:
            A test requirements configuration or None if no such configuration
            was found for the given module.
        """
        if module.__name__ in self.tests:
            return self.tests[module.__name__]
        elif module.__package__ in self.tests:
            return self.tests[module.__package__]

        return None

    def check_requirements(
        self,
        module: ModuleType,
        environment: Optional[TestEnvironment] = None,
        client: Optional["Client"] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Check if all requirements for a test module are met in an environment.

        Args:
            module: A pytest test module.
            environment: An optional environment providing requirements.
                If not supplied, the active environment will be used.
            client: An optional ZenML client already connected to the
                environment, to be reused. If not provided, a new client will be
                created and configured to connect to the environment.

        Returns:
            The true/false result and a message describing which requirements
            are not met.
        """
        test_config = self._get_test_module_requirements(module)
        if test_config is None:
            # Use an empty requirements configuration if no requirements are
            # specified for the test module in the configuration.
            test_config = TestConfig(module=module.__name__)

        logging.info(f"Checking requirements for '{test_config.module}'")

        if environment is None:
            client = None
            environment = self.active_environment

        if client is None:
            with environment.deployment.connect() as client:
                return test_config.check_requirements(
                    client=client, environment=environment
                )

        return test_config.check_requirements(
            client=client, environment=environment
        )

    @contextmanager
    def setup_test_stack(
        self,
        module: ModuleType,
        environment: Optional[TestEnvironment] = None,
        client: Optional["Client"] = None,
        cleanup: bool = True,
    ) -> Generator["Stack", None, None]:
        """Provision and activate a ZenML stack for a test module.

        Args:
            module: A pytest test module.
            environment: An optional environment to be used to setup the stack.
                If not supplied, the active environment will be used.
            client: An optional ZenML client already connected to the
                environment, to be reused. If not provided, a new client will be
                created and configured to connect to the environment.
            cleanup: Whether to clean up the stack after the test.

        Yields:
            Stack: The active stack that the test should use.
        """
        test_config = self._get_test_module_requirements(module)
        if test_config is None:
            # Use an empty requirements configuration if no requirements are
            # specified for the test module in the configuration.
            test_config = TestConfig(module=module.__name__)

        if environment is None:
            client = None
            environment = self.active_environment

        if client is None:
            with environment.deployment.connect() as client:
                with test_config.setup_test_stack(
                    client=client,
                    module=module,
                    environment=environment,
                    cleanup=cleanup,
                ) as stack:
                    yield stack

        with test_config.setup_test_stack(
            client=client,
            module=module,
            environment=environment,
            cleanup=cleanup,
        ) as stack:
            yield stack
