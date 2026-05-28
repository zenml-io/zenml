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
"""Base abstractions for ZenML sandbox stack components.

A Sandbox is a stack component a step *uses* (not one that runs the
step) to execute code in an isolated environment. See ``plan.md`` and
ADR 0001 for the component-vs-launcher framing rationale.
"""

from abc import ABC, abstractmethod
from typing import (
    Any,
    Dict,
    Optional,
    Type,
    cast,
)

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.sandboxes.session import SandboxSession
from zenml.sandboxes.snapshot import BaseSandboxSnapshot
from zenml.stack.flavor import Flavor
from zenml.stack.stack_component import StackComponent, StackComponentConfig

logger = get_logger(__name__)


# Sentinel: when used as ``base_image``, the Session uses the image the
# current ZenML step is running in. Falls back to flavor default with a
# warning if the step is not containerized. See plan.md "Session Environment".
STEP_IMAGE = "<step>"


class BaseSandboxConfig(StackComponentConfig):
    """Base configuration for sandbox stack components.

    Default env vars and stored secrets that should be injected into every
    Session are configured on the StackComponent itself, not here — see
    ``StackComponent.environment`` and ``StackComponent.secrets`` (set via
    ``zenml stack-component register --env ... --secret ...``). Flavors read
    those at ``create_session()`` time and pass them through to the provider.
    """

    @property
    def is_remote(self) -> bool:
        """Sandboxes are called from inside step code, not from the server.

        Unlike orchestrators and step operators, the ZenML server does not
        need to reach the sandbox.
        """
        return False

    @property
    def is_local(self) -> bool:
        """Inverse of ``is_remote``.

        Returns:
            Whether this sandbox component is local-only.
        """
        return not self.is_remote


class BaseSandboxSettings(BaseSettings):
    """Per-step / per-pipeline overrides for a Sandbox component."""

    base_image: Optional[str] = Field(
        default=None,
        description="Image for the Session. None → flavor default; the "
        "sentinel STEP_IMAGE → image the current ZenML step is running in "
        "(warns and falls back to flavor default if not containerized); "
        "any other string → exact image URI. STEP_IMAGE resolution only "
        "fires for static containerized pipelines (the non-dynamic submit "
        "path); dynamic pipelines and the legacy prepare_or_run_pipeline "
        "path silently fall back to the flavor default.",
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-step env vars merged into the Session on top of "
        "the component's `StackComponent.environment` and resolved "
        "secrets (settings override on key collision). For secret-backed "
        "values, attach a secret to the component via "
        "`zenml sandbox register --secret=...`.",
    )
    copy_local_env: bool = Field(
        default=False,
        description="If True, propagates the step process's full local env "
        "into the Session. Layered FIRST in the env merge — explicit "
        "component env, component secrets, and per-step "
        "settings.environment all override values copied from the local "
        "env. Convenient for prototyping; off by default for security.",
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        description="Session-level timeout passed through to the provider's "
        "TTL knob. None lets the provider apply its own default.",
    )


class BaseSandbox(StackComponent, ABC):
    """Base class for all ZenML sandbox components.

    See ADR 0001 (component-vs-launcher) and ADR 0002 (attach vs restore) in
    ``plan.md``.
    """

    # ------------------------- typed config / settings --------------------

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
            ``BaseSandboxSettings``. Flavors may override to expose
            flavor-specific fields.
        """
        return BaseSandboxSettings

    # ------------------------- abstract surface ---------------------------

    @abstractmethod
    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Creates a fresh Session, applying config + settings.

        Implementations typically delegate the settings merge to
        ``self.resolve_settings(settings)`` and the env merge to
        ``self._resolve_session_environment(...)`` before calling the
        provider's primitive.
        """

    def attach(self, session_id: str) -> SandboxSession:
        """Reconnects to an already-live Session by id.

        Cheap (no snapshot needed). Use for subagent / cross-pipeline flows.
        Optional; default raises NotImplementedError.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support session attach."
        )

    def restore(self, snapshot: BaseSandboxSnapshot) -> SandboxSession:
        """Materializes a new Session from a stored Snapshot.

        Returns a *new* Session (fresh id); the original is unaffected.
        Subclasses that support restore should call
        ``self._validate_snapshot_provider(snapshot)`` first, then
        materialize from the provider primitive.

        Args:
            snapshot: The snapshot to restore from.

        Returns:
            A new ``SandboxSession`` materialized from the snapshot.

        Raises:
            NotImplementedError: Default — flavors opt in by overriding.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support restore."
        )

    # ------------------------- settings resolution ------------------------

    def resolve_settings(
        self, override: Optional[BaseSandboxSettings] = None
    ) -> BaseSandboxSettings:
        """Returns the effective sandbox settings.

        Reuses the canonical ``StackComponent.get_settings(step_run)``
        which already layers config defaults under the step's
        ``settings[<canonical-key>]`` entry and validates against this
        flavor's ``settings_class``.

        Args:
            override: Explicit per-call settings. If provided, they are
                layered on top of the config defaults exactly the same
                way ``get_settings`` does for the step container.
                Otherwise the active step context is consulted; if
                there is no step context either, the config defaults
                are returned as-is.

        Returns:
            The effective settings for the next Session.
        """
        from zenml.steps.step_context import StepContext

        settings_cls = self.settings_class or BaseSandboxSettings

        if override is not None:
            settings_dict = self.config.model_dump(exclude_unset=True)
            settings_dict.update(override.model_dump(exclude_unset=True))
            return cast(
                BaseSandboxSettings,
                settings_cls.model_validate(settings_dict),
            )

        ctx = StepContext.get()
        if ctx is not None:
            return cast(BaseSandboxSettings, self.get_settings(ctx.step_run))

        return cast(
            BaseSandboxSettings,
            settings_cls.model_validate(
                self.config.model_dump(exclude_unset=True)
            ),
        )

    # ------------------------- env / secret merging -----------------------

    def _resolve_session_environment(
        self, settings: Optional[BaseSandboxSettings]
    ) -> Dict[str, str]:
        """Composes env vars to inject into a new Session.

        Layers (later sources override earlier on key collision):

        1. ``os.environ`` of the step process, if
           ``settings.copy_local_env`` is True.
        2. ``self.environment`` — component-level env vars (already
           secret-ref-resolved by ``SecretReferenceMixin``).
        3. ``self.secrets`` — component-level secret UUIDs exploded
           into env vars via ``Client().get_secret(...).secret_values``.
        4. ``settings.environment`` — per-step plain overrides.

        For step-runtime env (every stack component's env merged), use
        ``zenml.utils.env_utils.get_runtime_environment`` instead — this
        helper is intentionally scoped to *this* component since the
        Sandbox runs in its own provider, not the step container.

        Args:
            settings: Effective per-step settings (or None to skip the
                ``copy_local_env`` + ``settings.environment`` layers).

        Returns:
            The merged ``Dict[str, str]`` to pass to the provider.
        """
        import os

        from zenml.client import Client

        env: Dict[str, str] = {}
        if settings is not None and settings.copy_local_env:
            env.update(os.environ)
        env.update(self.environment or {})
        for secret_id in self.secrets or []:
            try:
                env.update(Client().get_secret(secret_id).secret_values)
            except Exception as e:
                logger.warning(
                    "Could not resolve sandbox component secret %s: %s. "
                    "Skipping.",
                    secret_id,
                    e,
                )
        if settings is not None and settings.environment:
            env.update(settings.environment)
        return env

    # ------------------------- snapshot helpers ---------------------------

    def _validate_snapshot_provider(
        self, snapshot: BaseSandboxSnapshot
    ) -> None:
        """Asserts a snapshot was produced by this component's flavor.

        Subclasses that implement ``restore`` call this helper first to
        reject cross-flavor snapshots with a clear error message before
        invoking their provider's restore primitive.

        Args:
            snapshot: The snapshot to validate.

        Raises:
            ValueError: If ``snapshot.provider`` does not match this
                component's flavor.
        """
        if snapshot.provider != self.flavor:
            raise ValueError(
                f"Cannot restore snapshot from provider '{snapshot.provider}' "
                f"on a '{self.flavor}' sandbox component."
            )


class BaseSandboxFlavor(Flavor):
    """Base flavor contract for sandbox implementations."""

    @property
    def type(self) -> StackComponentType:
        """Stack component type.

        Returns:
            ``StackComponentType.SANDBOX``.
        """
        return StackComponentType.SANDBOX

    @property
    def config_class(self) -> Type[BaseSandboxConfig]:
        """Default config class for sandbox flavors.

        Returns:
            ``BaseSandboxConfig``. Concrete flavors typically override.
        """
        return BaseSandboxConfig

    @property
    def implementation_class(self) -> Type[BaseSandbox]:
        """Concrete sandbox implementation class.

        Subclasses must override and return their concrete ``BaseSandbox``
        subclass.

        Raises:
            NotImplementedError: Always — subclasses must override.
        """
        raise NotImplementedError(
            "Concrete sandbox flavors must override implementation_class."
        )
