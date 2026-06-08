#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Base sandbox flavor and component."""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Type, cast

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.sandboxes.session import SandboxSession
from zenml.sandboxes.snapshot import SandboxSnapshot
from zenml.stack.flavor import Flavor
from zenml.stack.stack_component import StackComponent, StackComponentConfig

logger = get_logger(__name__)


class BaseSandboxSettings(BaseSettings):
    """Sandbox settings."""

    sandbox_environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set in the sandbox.",
    )


class BaseSandboxConfig(StackComponentConfig):
    """Sandbox configuration."""

    @property
    def is_local(self) -> bool:
        """Whether this sandbox component is running locally.

        Returns:
            Whether this sandbox component is running locally.
        """
        return not self.is_remote


class BaseSandbox(StackComponent, ABC):
    """Base class for all ZenML sandbox components."""

    @property
    def config(self) -> BaseSandboxConfig:
        """The sandbox component configuration.

        Returns:
            The sandbox component configuration.
        """
        return cast(BaseSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """The sandbox settings class.

        Returns:
            The sandbox settings class.
        """
        return BaseSandboxSettings

    @abstractmethod
    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Create a fresh sandbox session.

        Args:
            settings: The sandbox settings.

        Returns:
            A new sandbox session.
        """

    def attach(self, session_id: str) -> SandboxSession:
        """Attach to a running sandbox session.

        Args:
            session_id: The ID of the running sandbox session.

        Raises:
            NotImplementedError: If the sandbox does not support attaching to a
                running sandbox session.

        Returns:
            Sandbox session.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support attaching to a running "
            "sandbox session."
        )

    def restore(self, snapshot: SandboxSnapshot) -> SandboxSession:
        """Restore a sandbox session from a snapshot.

        Args:
            snapshot: The snapshot to restore from.

        Raises:
            NotImplementedError: If the sandbox does not support restoring from
                a snapshot.

        Returns:
            Sandbox session.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support restoring from a snapshot."
        )

    def resolve_settings(
        self, override: Optional[BaseSandboxSettings] = None
    ) -> BaseSandboxSettings:
        """Resolve the sandbox settings.

        Args:
            override: Per-call settings override. If provided these will
                override values in the component settings/config.

        Returns:
            The resolved settings.
        """
        from zenml.steps.step_context import StepContext

        if step_context := StepContext.get():
            settings_dict = self.get_settings(
                step_context.step_run
            ).model_dump(exclude_unset=True)
        else:
            settings_dict = self.config.model_dump(exclude_unset=True)

        if override is not None:
            settings_dict.update(override.model_dump(exclude_unset=True))

        assert self.settings_class is not None
        return cast(
            BaseSandboxSettings,
            self.settings_class.model_validate(settings_dict),
        )

    def _resolve_session_environment(
        self, settings: BaseSandboxSettings
    ) -> Dict[str, str]:
        """Resolve environment variables to inject into a new sandbox session.

        Args:
            settings: Sandbox settings.

        Returns:
            Environment variables.
        """
        return settings.sandbox_environment

    def _validate_snapshot(self, snapshot: SandboxSnapshot) -> None:
        """Validate that a snapshot can be restored by this component.

        Args:
            snapshot: The snapshot to validate.

        Raises:
            ValueError: If the snapshot cannot be restored by this component.
        """
        if snapshot.sandbox_id != self.id:
            raise ValueError(
                f"Cannot restore snapshot from sandbox '{snapshot.sandbox_id}' "
                f"on a different sandbox '{self.id}'."
            )


class BaseSandboxFlavor(Flavor):
    """Base sandbox flavor."""

    @property
    def type(self) -> StackComponentType:
        """Stack component type.

        Returns:
            `StackComponentType.SANDBOX`.
        """
        return StackComponentType.SANDBOX

    @property
    def config_class(self) -> Type[BaseSandboxConfig]:
        """Configuration class.

        Returns:
            The configuration class.
        """
        return BaseSandboxConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseSandbox]:
        """Implementation class.

        Returns:
            The implementation class.
        """
