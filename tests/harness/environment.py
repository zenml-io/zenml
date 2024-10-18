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
"""ZenML test environment management."""

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Dict, Generator, List, Optional
from uuid import UUID

from tests.harness.deployment.base import BaseTestDeployment
from tests.harness.model import EnvironmentConfig
from tests.harness.model.requirements import StackRequirement, TestRequirements
from zenml.enums import StackComponentType

if TYPE_CHECKING:
    from zenml.client import Client
    from zenml.models import ComponentResponse


class TestEnvironment:
    """ZenML test environment."""

    def __init__(
        self,
        config: EnvironmentConfig,
        deployment: BaseTestDeployment,
    ) -> None:
        """Initialize the test environment.

        Args:
            config: The environment configuration.
            deployment: The deployment configured for this environment.
        """
        self.config = config
        self.deployment = deployment
        self._optional_components: Optional[
            Dict[StackComponentType, List[ComponentResponse]]
        ] = None
        self._mandatory_components: Optional[
            Dict[StackComponentType, List[ComponentResponse]]
        ] = None

    @property
    def is_running(self) -> bool:
        """Returns whether the environment is running.

        Returns:
            Whether the environment is running.
        """
        return self.deployment.is_running

    @property
    def is_provisioned(self) -> bool:
        """Returns whether the environment is provisioned.

        Returns:
            Whether the environment is provisioned.
        """
        if self.is_disabled or not self.deployment.is_running:
            return False

        with self.deployment.connect() as client:
            component_requirements: List[StackRequirement] = []

            for requirement in self.config.compiled_requirements:
                if not requirement.mandatory:
                    # optional components the software requirements of which are
                    # not met locally do not need to exist for the environment
                    # to be considered provisioned
                    result, _ = requirement.check_software_requirements()
                    if not result:
                        continue

                component_requirements.extend(requirement.stacks)

            for component_requirement in component_requirements:
                component_model = component_requirement.find_stack_component(
                    client=client,
                )
                if component_model is None:
                    return False

        return True

    @property
    def is_disabled(self) -> bool:
        """Returns whether the environment is administratively disabled.

        Returns:
            Whether the environment is administratively disabled.
        """
        return self.config.disabled or self.deployment.config.disabled

    def _collect_components(
        self,
    ) -> None:
        """Collect the components managed or tracked by this environment."""
        with self.deployment.connect() as client:
            self._optional_components = {}
            self._mandatory_components = {}

            optional_stack_requirements: List[StackRequirement] = []
            mandatory_stack_requirements: List[StackRequirement] = []
            for requirement in self.config.compiled_requirements:
                assert isinstance(requirement, TestRequirements)

                # components the software requirements of which are
                # not met locally are ignored
                result, _ = requirement.check_software_requirements()
                if not result:
                    continue
                if requirement.mandatory:
                    mandatory_stack_requirements.extend(requirement.stacks)
                else:
                    optional_stack_requirements.extend(requirement.stacks)

            for comp_map, req_list in [
                (self._optional_components, optional_stack_requirements),
                (self._mandatory_components, mandatory_stack_requirements),
            ]:
                for stack_requirement in req_list:
                    component_model = stack_requirement.find_stack_component(
                        client=client,
                    )

                    if component_model:
                        comp_map.setdefault(
                            component_model.type,
                            [],
                        ).append(component_model)

    @property
    def optional_components(
        self,
    ) -> Dict[StackComponentType, List["ComponentResponse"]]:
        """Returns the optional components managed or tracked by this environment.

        Returns:
            A dictionary mapping component types to a list of optional
            components.
        """
        if self._optional_components is not None:
            return self._optional_components

        self._collect_components()
        assert self._optional_components is not None
        return self._optional_components

    @property
    def mandatory_components(
        self,
    ) -> Dict[StackComponentType, List["ComponentResponse"]]:
        """Returns the mandatory components managed or tracked by this environment.

        Returns:
            A dictionary mapping component types to a list of mandatory
            components.

        Raises:
            AssertionError: If the components have not been collected yet.
        """
        if self._mandatory_components is not None:
            return self._mandatory_components

        self._collect_components()

        assert self._mandatory_components is not None
        return self._mandatory_components

    @property
    def components(
        self,
    ) -> Dict[StackComponentType, List["ComponentResponse"]]:
        """Returns the components managed or tracked by this environment.

        Returns:
            A dictionary mapping component types to a list of components.
        """
        return {
            **self.optional_components,
            **self.mandatory_components,
        }

    def up(self) -> None:
        """Start the deployment for this environment.

        Raises:
            RuntimeError: If the environment is disabled.
        """
        if self.is_disabled:
            raise RuntimeError(
                "Cannot start a disabled environment. Please enable "
                "the environment in the configuration and try again."
            )

        self.deployment.up()

    def provision(self) -> None:
        """Start the deployment for this environment and provision the stack components.

        Raises:
            RuntimeError: If the environment is disabled or if a mandatory
                component cannot be provisioned.
        """
        if self.is_disabled:
            raise RuntimeError(
                "Cannot provision a disabled environment. Please enable "
                "the environment in the configuration and try again."
            )

        self.deployment.up()

        build_base_image: bool = False

        with self.deployment.connect() as client:
            component_requirements: List[StackRequirement] = []
            components: List["ComponentResponse"] = []

            for requirement in self.config.compiled_requirements:
                result, err = requirement.check_software_requirements()
                if not result:
                    if requirement.mandatory:
                        raise RuntimeError(
                            f"Software requirement '{requirement.name}' not "
                            f"met for environment '{self.config.name}': {err}. "
                            f"Please install the required software packages "
                            f"and tools and try again."
                        )
                    else:
                        # optional components the software requirements of which
                        # are not met locally are ignored
                        logging.warning(
                            f"Software requirement '{requirement.name}' not "
                            f"met for environment '{self.config.name}': {err}. "
                            f"This requirement is not mandatory, but may cause "
                            f"some tests to be skipped."
                        )
                        continue

                component_requirements.extend(requirement.stacks)

            for component_requirement in component_requirements:
                if component_requirement.containerized:
                    build_base_image = True

                # Environment requirements are managed by the test framework
                # by default
                external = component_requirement.external or False

                component_model = component_requirement.find_stack_component(
                    client=client,
                )
                if component_model is not None:
                    logging.info(
                        f"Reusing existing {component_model.type.value} stack "
                        f"component '{component_model.name}'"
                    )
                elif not external:
                    component_model = component_requirement.register_component(
                        client=client,
                    )
                    logging.info(
                        f"Registered {component_model.type.value} stack "
                        f"component '{component_model.name}'"
                    )
                else:
                    raise RuntimeError(
                        f"Could not find external "
                        f"{component_requirement.type.value} "
                        f"stack component '{component_requirement.name}' "
                        f"matching the environment requirements."
                    )
                components.append(component_model)

            if build_base_image:
                BaseTestDeployment.build_base_image()

    def deprovision(self) -> None:
        """Deprovision all stack components for this environment.

        Raises:
            RuntimeError: If the environment is disabled.
        """
        if self.is_disabled:
            raise RuntimeError(
                "Cannot deprovision a disabled environment. Please enable "
                "the environment in the configuration and try again."
            )

        if not self.is_running:
            logging.info(
                f"Environment '{self.config.name}' is not running, "
                f"skipping deprovisioning."
            )
            return

        with self.deployment.connect() as client:
            component_requirements: List[StackRequirement] = []
            components: List["ComponentResponse"] = []
            external_components: List[UUID] = []

            for requirement in self.config.compiled_requirements:
                # components the software requirements of which are
                # not met locally are ignored
                result, _ = requirement.check_software_requirements()
                if not result:
                    continue

                component_requirements.extend(requirement.stacks)

            for component_requirement in component_requirements:
                # Environment requirements are managed by the test framework
                # by default
                external = component_requirement.external or False

                component_model = component_requirement.find_stack_component(
                    client=client,
                )
                if component_model is None:
                    logging.info(
                        f"{component_requirement.type.value} stack component "
                        f"{component_requirement.name} is no longer registered."
                    )
                else:
                    components.append(component_model)
                    if external:
                        external_components.append(component_model.id)

            for component_model in components:
                if component_model.id not in external_components:
                    logging.info(
                        f"Deleting {component_model.type.value} stack "
                        f"component '{component_model.name}'"
                    )
                    client.zen_store.delete_stack_component(component_model.id)
                else:
                    logging.info(
                        f"Skipping deletion of external "
                        f"{component_model.type.value} stack component "
                        f"'{component_model.name}'"
                    )

    def down(self) -> None:
        """Deprovision stacks and stop the deployment for this environment.

        Raises:
            RuntimeError: If the environment is disabled.
        """
        if self.is_disabled:
            raise RuntimeError(
                "Cannot stop a disabled environment. Please enable "
                "the environment in the configuration and try again."
            )

        self.deprovision()
        self.deployment.down()

    def cleanup(self) -> None:
        """Clean up the deployment for this environment."""
        self.deprovision()
        self.deployment.cleanup()

    @contextmanager
    def setup(
        self,
        teardown: bool = True,
        deprovision: bool = True,
    ) -> Generator["Client", None, None]:
        """Context manager to provision the environment and optionally tear it down afterwards.

        Args:
            teardown: Whether to tear down the environment on exit (implies
                deprovision=True). If the environment is already running on
                entry, it will not be torn down.
            deprovision: Whether to deprovision and delete the environment
                stack components on exit. If the environment is already
                provisioned on entry, it will not be deprovisioned.

        Yields:
            A ZenML client connected to the environment.

        Raises:
            RuntimeError: If the environment is disabled.
            Exception: The exception caught during provisioning.
        """
        if self.is_disabled:
            raise RuntimeError(
                "Cannot use a disabled environment. Please enable "
                "the environment in the configuration and try again."
            )

        if self.is_running:
            if teardown:
                deprovision = True
            teardown = False
        if self.is_provisioned:
            deprovision = False

        try:
            self.provision()
        except Exception as e:
            logging.error(
                f"Failed to provision environment '{self.config.name}': {e}"
            )
            try:
                if teardown:
                    self.cleanup()
                elif deprovision:
                    self.deprovision()
            except Exception as e1:
                logging.error(
                    f"Failed to cleanup environment '{self.config.name}': {e1}"
                )
                raise e1
            raise e

        with self.deployment.connect() as client:
            yield client

        try:
            if teardown:
                self.cleanup()
            elif deprovision:
                self.deprovision()
        except Exception as e:
            logging.error(
                f"Failed to cleanup environment '{self.config.name}': {e}"
            )
            raise e
