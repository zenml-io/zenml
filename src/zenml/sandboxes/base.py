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

from pydantic import Field, ValidationError

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
        description="Per-step env vars merged into the Session on top of the "
        "component's `StackComponent.environment` (settings override on key "
        "collision). Values may reference ZenML secrets via "
        "{{secret_name.key}}.",
    )
    copy_local_env: bool = Field(
        default=False,
        description="If True, propagates the step process's full local env "
        "(including any resolved ZenML secrets present) into the Session. "
        "Layered FIRST in the env merge — explicit component env, "
        "component secrets, and per-step settings.environment all override "
        "values copied from the local env. Convenient for prototyping; off "
        "by default for security.",
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
        ``self.effective_settings(settings)`` and the env merge to
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

    def pull_step_settings(self) -> Optional[BaseSandboxSettings]:
        """Returns the active step's sandbox settings, if any.

        Lets flavors fall back to the per-step settings configured via
        ``@step(settings={"sandbox[.<flavor>|:<name>]": ...})`` when a
        caller invokes ``create_session()`` without an explicit override.
        Returns ``None`` when there is no active step context or when
        the step did not declare sandbox settings.

        ZenML accepts three settings key forms: ``"sandbox"`` (any
        flavor), ``"sandbox.<flavor>"`` (only this flavor), and
        ``"sandbox:<name>"`` (only this component instance). All three
        are checked in increasing specificity so a more specific key
        wins if both are present.

        Returns:
            The step's sandbox settings (already validated against the
            flavor's ``settings_class``) or ``None``.
        """
        from zenml.steps.step_context import StepContext

        ctx = StepContext.get()
        if ctx is None:
            return None

        settings_cls = self.settings_class
        if settings_cls is None or not issubclass(
            settings_cls, BaseSandboxSettings
        ):
            return None

        raw: Optional[BaseSettings] = None
        step_settings = ctx.step_run.config.settings
        for key in (
            "sandbox",
            f"sandbox.{self.flavor}",
            f"sandbox:{self.name}",
        ):
            if key in step_settings:
                raw = step_settings[key]
        if raw is None:
            return None

        if isinstance(raw, settings_cls):
            return raw
        try:
            return settings_cls.model_validate(
                raw.model_dump(exclude_unset=True)
            )
        except ValidationError as e:
            logger.debug(
                "Could not coerce step sandbox settings to %s: %s",
                settings_cls.__name__,
                e,
            )
            return None

    def effective_settings(
        self,
        override: Optional[BaseSandboxSettings] = None,
    ) -> BaseSandboxSettings:
        """Resolves effective settings = config defaults + override.

        Generic 3-step pipeline used by every flavor:

        1. If ``override`` is ``None``, fall back to per-step settings
           via ``pull_step_settings()``.
        2. Layer the config's settings-shaped defaults under the override
           so only fields the caller explicitly set on the override are
           applied (``exclude_unset=True``).
        3. Validate the result through the flavor's ``settings_class``.

        Flavors with a settings class that inherits from both ``Config``
        and ``Settings`` get the config defaults included automatically.

        Args:
            override: Optional per-step settings; if omitted the step
                context is consulted.

        Returns:
            The effective settings for this Session.
        """
        if override is None:
            override = self.pull_step_settings()
        settings_cls = self.settings_class
        if settings_cls is None or not issubclass(
            settings_cls, BaseSandboxSettings
        ):
            # Should not happen for a sandbox flavor, but fall back
            # gracefully rather than crash.
            return override or BaseSandboxSettings()

        # Only carry over config fields that the settings class actually
        # declares — config may extend with non-settings fields.
        base = self.config.model_dump(
            include=set(settings_cls.model_fields.keys())
        )
        if override is not None:
            base.update(override.model_dump(exclude_unset=True))
        return settings_cls(**base)

    # ------------------------- env / secret merging -----------------------

    def _resolve_session_environment(
        self, settings: Optional[BaseSandboxSettings]
    ) -> Dict[str, str]:
        """Merges env vars from all sources for a new Session.

        Order (later sources override earlier on key collision — most-specific
        wins, matching ``get_runtime_environment`` precedent):

        1. ``os.environ`` of the step process, if ``settings.copy_local_env``
           is ``True``. Layered first so explicit configuration always wins.
        2. ``StackComponent.environment`` (component-level explicit env vars).
        3. Each UUID in ``StackComponent.secrets`` resolved via the ZenML
           secret store and exploded into env vars (every key in the secret
           becomes one ``$KEY=value`` entry).
        4. ``settings.environment`` — per-step overrides. Values may be ZenML
           ``{{secret_name.key}}`` references, resolved here. Highest
           precedence.

        Args:
            settings: Effective per-step settings, or ``None`` (use defaults).

        Returns:
            The merged ``Dict[str, str]`` to pass to the provider.
        """
        import os

        from zenml.client import Client
        from zenml.utils import secret_utils

        merged: Dict[str, str] = {}

        # 1. Local env first — explicit configuration below will overwrite.
        if settings is not None and settings.copy_local_env:
            merged.update(os.environ)

        # 2. Component-level explicit env vars.
        merged.update(self.environment or {})

        # 3. Component-level secrets exploded.
        client: Optional["Client"] = None
        if self.secrets or (settings is not None and settings.environment):
            client = Client()

        if self.secrets and client is not None:
            for secret_id in self.secrets:
                try:
                    secret = client.get_secret(secret_id)
                except Exception as e:
                    logger.warning(
                        "Could not resolve sandbox component secret %s: %s. "
                        "Skipping.",
                        secret_id,
                        e,
                    )
                    continue
                merged.update(secret.secret_values)

        # 4. Per-step overrides (highest precedence). Secret references
        # in values get resolved against the secret store.
        if (
            settings is not None
            and settings.environment
            and client is not None
        ):
            for key, value in settings.environment.items():
                if secret_utils.is_secret_reference(value):
                    ref = secret_utils.parse_secret_reference(value)
                    try:
                        secret = client.get_secret_by_name_and_private_status(
                            name=ref.name
                        )
                        merged[key] = secret.secret_values[ref.key]
                    except Exception as e:
                        logger.warning(
                            "Could not resolve secret reference %r for env "
                            "var '%s': %s. Skipping.",
                            value,
                            key,
                            e,
                        )
                else:
                    merged[key] = value

        return merged

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
