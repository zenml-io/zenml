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
"""ZenML test configuration models."""

import itertools
import logging
from contextlib import contextmanager
from types import ModuleType
from typing import TYPE_CHECKING, Dict, Generator, List, Optional, Tuple, Union
from uuid import UUID

from pydantic import Field

from tests.harness.model.base import BaseTestConfigModel
from tests.harness.model.requirements import StackRequirement, TestRequirements

if TYPE_CHECKING:
    from tests.harness.environment import TestEnvironment
    from tests.harness.harness import TestHarness
    from zenml.client import Client
    from zenml.stack import Stack


class TestConfig(BaseTestConfigModel):
    """ZenML test module configuration."""

    module: str
    description: str = ""
    disabled: bool = False
    requirements: List[Union[str, TestRequirements]] = Field(
        default_factory=list
    )

    def compile(self, harness: "TestHarness") -> None:
        """Validates and compiles the configuration when part of a test harness.

        Checks that the referenced requirements exist in the test harness
        configuration and replaces them with the actual configuration objects.

        Args:
            harness: The test harness to validate against.

        Raises:
            ValueError: If one of the requirements does not exist in the test
                harness configuration.
        """
        for i, config in enumerate(self.requirements):
            if isinstance(config, str):
                cfg = harness.get_global_requirements(config)
                if cfg is None:
                    raise ValueError(
                        f"Requirement '{config}' referenced by test "
                        f"configuration for module {self.module} does not "
                        f"exist."
                    )
                self.requirements[i] = cfg
            else:
                config.compile(harness)

    @property
    def compiled_requirements(self) -> List[TestRequirements]:
        """Get the compiled requirements.

        Returns:
            The compiled requirements.
        """
        return [
            req
            for req in self.requirements
            if isinstance(req, TestRequirements)
        ]

    def check_requirements(
        self,
        client: "Client",
        environment: "TestEnvironment",
    ) -> Tuple[bool, Optional[str]]:
        """Check if all requirements are met.

        Args:
            client: A ZenML client to be used to check ZenML requirements.
            environment: The environment providing the requirements.

        Returns:
            The true/false result and a message describing which requirements
            are not met.
        """
        if self.disabled:
            return False, "Test is disabled in the configuration."
        for req in self.compiled_requirements:
            result, message = req.check_requirements(
                client, environment=environment
            )
            if not result:
                return result, message

        return True, None

    @contextmanager
    def setup_test_stack(
        self,
        client: "Client",
        environment: "TestEnvironment",
        module: Optional[ModuleType] = None,
        cleanup: bool = True,
    ) -> Generator["Stack", None, None]:
        """Provision and activate a ZenML stack for this test.

        Args:
            module: A pytest test module.
            client: The ZenML client to be used to configure the ZenML stack.
            environment: The environment providing the stack requirements.
            cleanup: Whether to clean up the stack after the test.

        Yields:
            The active stack that the test should use.

        Raises:
            RuntimeError: If the stack requirements are not met or if multiple
                stack components of the same type are specified as requirements.
            Exception: The exception raised while provisioning the stack.
        """
        from zenml.enums import StackComponentType
        from zenml.utils.string_utils import random_str

        components: Dict[StackComponentType, Union[str, UUID]] = {}

        stack_requirements = [req.stacks for req in self.compiled_requirements]
        requirements = itertools.chain.from_iterable(stack_requirements)

        for stack_requirement in requirements:
            component = stack_requirement.find_stack_component(
                client, environment=environment
            )
            if component is None:
                # This should not happen if the requirements are checked
                # before calling this method.
                raise RuntimeError(
                    f"could not find a stack component that matches the test "
                    f"requirements '{stack_requirement}'."
                )
            if component.type in components:
                raise RuntimeError(
                    f"multiple stack components of type '{component.type}' "
                    f"are specified as requirements by the test requirements."
                )
            components[component.type] = component.id

        # Every stack needs an orchestrator and an artifact store.
        for component_type in [
            StackComponentType.ORCHESTRATOR,
            StackComponentType.ARTIFACT_STORE,
        ]:
            if component_type not in components:
                requirement = StackRequirement(
                    type=component_type,
                )
                component = requirement.find_stack_component(
                    client, environment=environment
                )

                # There is always a default orchestrator and artifact store.
                assert component is not None
                components[component_type] = component.id

        # Add remaining components enforced by the test environment.
        for (
            component_type,
            mandatory_components,
        ) in environment.mandatory_components.items():
            if component_type not in components:
                components[component_type] = mandatory_components[0].id

        random_name = "pytest-"
        if module is not None:
            random_name = random_name + module.__name__.split(".")[-1]
        random_name = random_name + f"-{random_str(6).lower()}"

        logging.info(f"Configuring and provisioning stack '{random_name}'")

        # Register and activate the stack
        stack = client.create_stack(name=random_name, components=components)
        current_active_stack = client.active_stack_model.id
        client.activate_stack(stack.id)

        active_stack = client.active_stack
        logging.info(f"Using active stack '{stack.name}'")

        # Yield the stack
        yield active_stack

        # Activate the previous stack
        client.activate_stack(current_active_stack)

        # Delete the stack
        if cleanup:
            client.zen_store.delete_stack(stack.id)
