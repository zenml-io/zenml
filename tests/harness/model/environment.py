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
"""ZenML test environment models."""

from typing import TYPE_CHECKING, Dict, List, Union

from pydantic import Field

from tests.harness.model.base import BaseTestConfigModel
from tests.harness.model.deployment import DeploymentConfig
from tests.harness.model.requirements import TestRequirements

if TYPE_CHECKING:
    from tests.harness.environment import TestEnvironment
    from tests.harness.harness import TestHarness


class EnvironmentConfig(BaseTestConfigModel):
    """ZenML test environment settings."""

    name: str = Field(pattern="^[a-z][a-z0-9-_]+$")
    description: str = ""
    deployment: Union[str, DeploymentConfig]
    requirements: List[Union[str, TestRequirements]] = Field(
        default_factory=list
    )
    disabled: bool = False
    mandatory_requirements: List[Union[str, TestRequirements]] = Field(
        default_factory=list
    )
    capabilities: Dict[str, bool] = Field(default_factory=dict)

    def compile(self, harness: "TestHarness") -> None:
        """Validates and compiles the configuration when part of a test harness.

        Checks that the referenced deployment and requirements exist
        in the test harness configuration and replaces them with the
        actual configuration objects.

        Args:
            harness: The test harness to validate against.

        Raises:
            ValueError: If the referenced deployment or one of the requirements
                does not exist in the test harness configuration.
        """
        if isinstance(self.deployment, str):
            deployment = harness.get_deployment_config(self.deployment)
            if deployment is None:
                raise ValueError(
                    f"Deployment '{self.deployment}' referenced by environment "
                    f"'{self.name}' does not exist."
                )
            self.deployment = deployment

        for i, config in enumerate(self.requirements):
            if isinstance(config, str):
                cfg = harness.get_global_requirements(config)
                if cfg is None:
                    raise ValueError(
                        f"Requirement '{config}' referenced by environment "
                        f"'{self.name}' does not exist."
                    )

                cfg = cfg.model_copy()
                # Environment requirements are optional by default
                cfg.mandatory = cfg.mandatory or False
                self.requirements[i] = cfg
            else:
                # Environment requirements are optional by default
                config.mandatory = config.mandatory or False
                config.compile(harness)

        for i, config in enumerate(self.mandatory_requirements):
            if isinstance(config, str):
                cfg = harness.get_global_requirements(config)
                if cfg is None:
                    raise ValueError(
                        f"Mandatory requirement '{config}' referenced by "
                        f"environment '{self.name}' does not exist."
                    )

                # Set this requirement as mandatory
                cfg = cfg.model_copy()
                cfg.mandatory = True
                self.mandatory_requirements[i] = cfg
            else:
                config.mandatory = True
                config.compile(harness)

        self.compile_capabilities()

    def compile_capabilities(self) -> None:
        """Compile the capabilities of this environment."""
        capabilities = self.capabilities.copy()

        # Collect capabilities from environment requirements:
        #  - the environment capabilities override the requirement capabilities
        #  - if a requirement capability is set to None, it's interpreted as
        #   True
        #  - if a requirement capability is set to False, it overrides all
        #   other values
        for req in self.compiled_requirements:
            assert isinstance(req, TestRequirements)
            for cap, value in req.capabilities.items():
                value = value if value is not None else True
                if cap in self.capabilities:
                    continue
                capabilities[cap] = capabilities.get(cap, True) and value

        # Collect capabilities from the deployment:
        #  - the environment capabilities override the deployment capabilities
        #  - if a deployment capability is set to False, it overrides all other
        #   values
        assert isinstance(self.deployment, DeploymentConfig)
        for cap, value in self.deployment.capabilities.items():
            # The environment capabilities override the deployment capabilities
            if cap in self.capabilities:
                continue
            capabilities[cap] = capabilities.get(cap, True) and value

        self.capabilities = capabilities

    @property
    def compiled_requirements(self) -> List[TestRequirements]:
        """Get the compiled requirements.

        Returns:
            The compiled requirements.
        """
        return [
            req
            for req in self.requirements + self.mandatory_requirements
            if isinstance(req, TestRequirements)
        ]

    def has_capability(self, capability: str) -> bool:
        """Check if this environment has a capability.

        Args:
            capability: The capability to check.

        Returns:
            True if the environment has the capability, False otherwise.
        """
        return self.capabilities.get(capability, False)

    def get_environment(self) -> "TestEnvironment":
        """Instantiate a test environment based on this configuration.

        Returns:
            A test environment instance.
        """
        from tests.harness.environment import TestEnvironment
        from tests.harness.harness import TestHarness

        assert isinstance(self.deployment, DeploymentConfig)
        deployment = TestHarness().get_deployment(self.deployment.name)
        return TestEnvironment(config=self, deployment=deployment)
