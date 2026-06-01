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
"""Base abstractions for ZenML sandbox stack components."""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Type, cast

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.sandboxes.session import SandboxSession
from zenml.sandboxes.snapshot import BaseSandboxSnapshot
from zenml.stack.flavor import Flavor
from zenml.stack.stack_component import StackComponent, StackComponentConfig

logger = get_logger(__name__)


class BaseSandboxSettings(BaseSettings):
    """Per-step / per-pipeline overrides for a Sandbox component."""

    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-step env vars merged into the Session on top of "
        "the component's `StackComponent.environment` and resolved "
        "secrets. Settings override on key collision.",
    )
    copy_local_env: bool = Field(
        default=False,
        description="If True, propagates the step process's full local "
        "env into the Session. Layered FIRST in the env merge, so "
        "component env, component secrets, and per-step "
        "`settings.environment` all override values copied from the "
        "local env. Off by default for security.",
    )


class BaseSandboxConfig(BaseSandboxSettings, StackComponentConfig):
    """Base configuration for sandbox stack components.

    Inherits from `BaseSandboxSettings` so settings fields act as
    component-level defaults; per-step `BaseSandboxSettings` overrides
    them at session-creation time. Default env vars and secrets are
    configured on the StackComponent itself via
    `StackComponent.environment` / `StackComponent.secrets`.
    """

    @property
    def is_remote(self) -> bool:
        """Sandboxes are called from inside step code, not from the server.

        Unlike orchestrators and step operators, the ZenML server does
        not need to reach the sandbox.

        Returns:
            Whether this sandbox component is remote.
        """
        return False

    @property
    def is_local(self) -> bool:
        """Inverse of `is_remote`.

        Returns:
            Whether this sandbox component is local-only.
        """
        return not self.is_remote


class BaseSandbox(StackComponent, ABC):
    """Base class for all ZenML sandbox components."""

    @property
    def config(self) -> BaseSandboxConfig:
        """Typed sandbox component configuration.

        Returns:
            The component's config.
        """
        return cast(BaseSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for per-step / per-pipeline overrides.

        Returns:
            `BaseSandboxSettings`. Flavors may override to expose
            flavor-specific fields.
        """
        return BaseSandboxSettings

    @abstractmethod
    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Creates a fresh Session, applying config + settings.

        Implementations typically delegate the settings merge to
        `self.resolve_settings(settings)` and the env merge to
        `self._resolve_session_environment(...)` before calling the
        provider's primitive.
        """

    def attach(self, session_id: str) -> SandboxSession:
        """Reconnects to an already-live Session by id.

        No snapshot needed. Use for subagent or cross-pipeline flows.
        Optional. Default raises NotImplementedError.

        Args:
            session_id: Provider-issued id of the live session.

        Returns:
            A reconnected `SandboxSession`.

        Raises:
            NotImplementedError: Default. Flavors opt in by overriding.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support session attach."
        )

    def restore(self, snapshot: BaseSandboxSnapshot) -> SandboxSession:
        """Materializes a new Session from a stored Snapshot.

        Returns a new Session with a fresh id. The original is
        unaffected. Subclasses that support restore should call
        `self._validate_snapshot_provider(snapshot)` first, then
        materialize from the provider primitive.

        Args:
            snapshot: The snapshot to restore from.

        Returns:
            A new `SandboxSession` materialized from the snapshot.

        Raises:
            NotImplementedError: Default. Flavors opt in by overriding.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support restore."
        )

    def resolve_settings(
        self, override: Optional[BaseSandboxSettings] = None
    ) -> BaseSandboxSettings:
        """Returns the effective sandbox settings.

        Args:
            override: Explicit per-call settings. If provided, they are
                layered on top of the config defaults via the canonical
                `StackComponent._merge_settings` helper. Otherwise the
                active step context is consulted; if there is no step
                context either, the config defaults are returned as-is.

        Returns:
            The effective settings for the next Session.
        """
        from zenml.steps.step_context import StepContext

        if override is not None:
            return cast(
                BaseSandboxSettings,
                self._merge_settings(override.model_dump(exclude_unset=True)),
            )

        ctx = StepContext.get()
        if ctx is not None:
            return cast(BaseSandboxSettings, self.get_settings(ctx.step_run))

        return cast(BaseSandboxSettings, self._merge_settings({}))

    def _resolve_session_environment(
        self, settings: Optional[BaseSandboxSettings]
    ) -> Dict[str, str]:
        """Composes env vars to inject into a new Session.

        Layers (later sources override earlier on key collision):

        1. `os.environ` of the step process, if
           `settings.copy_local_env` is True.
        2. `self.environment` from the StackComponent.
        3. `self.secrets` from the StackComponent, resolved to
           env vars via `resolve_secrets_to_env`.
        4. `settings.environment`, per-step plain overrides.

        Args:
            settings: Effective per-step settings, or None to skip the
                `copy_local_env` + `settings.environment` layers.

        Returns:
            The merged `Dict[str, str]` to pass to the provider.
        """
        import os

        from zenml.utils.env_utils import resolve_secrets_to_env

        env: Dict[str, str] = {}
        if settings is not None and settings.copy_local_env:
            env.update(os.environ)
        env.update(self.environment or {})
        if self.secrets:
            env.update(resolve_secrets_to_env(list(self.secrets)))
        if settings is not None and settings.environment:
            env.update(settings.environment)
        return env

    def _validate_snapshot_provider(
        self, snapshot: BaseSandboxSnapshot
    ) -> None:
        """Asserts a snapshot was produced by this component.

        Rejects cross-flavor snapshots, plus (when `component_id` is
        set on the snapshot) cross-component snapshots whose
        provider-side ref is not portable to this component. Subclasses
        call this first in `restore` before invoking the provider's
        restore primitive.

        Args:
            snapshot: The snapshot to validate.

        Raises:
            ValueError: If `snapshot.sandbox_flavor` does not match
                this component's flavor, or `snapshot.component_id`
                is set and does not match this component's id.
        """
        if snapshot.sandbox_flavor != self.flavor:
            raise ValueError(
                f"Cannot restore snapshot from flavor "
                f"'{snapshot.sandbox_flavor}' on a '{self.flavor}' "
                "sandbox component."
            )
        if (
            snapshot.component_id is not None
            and snapshot.component_id != self.id
        ):
            raise ValueError(
                f"Cannot restore snapshot from component "
                f"'{snapshot.component_id}' on a different component "
                f"'{self.id}'."
            )


class BaseSandboxFlavor(Flavor):
    """Base flavor contract for sandbox implementations."""

    @property
    def type(self) -> StackComponentType:
        """Stack component type.

        Returns:
            `StackComponentType.SANDBOX`.
        """
        return StackComponentType.SANDBOX

    @property
    def config_class(self) -> Type[BaseSandboxConfig]:
        """Default config class for sandbox flavors.

        Returns:
            `BaseSandboxConfig`. Concrete flavors typically override.
        """
        return BaseSandboxConfig

    @property
    def implementation_class(self) -> Type[BaseSandbox]:
        """Concrete sandbox implementation class.

        Subclasses must override and return their concrete
        `BaseSandbox` subclass.

        Raises:
            NotImplementedError: Always. Subclasses must override.
        """
        raise NotImplementedError(
            "Concrete sandbox flavors must override implementation_class."
        )
