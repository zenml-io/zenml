#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Capture configuration for ZenML."""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union


class ServingMode(str, Enum):
    """Serving mode enum."""

    BATCH = "BATCH"
    REALTIME = "REALTIME"


# Backwards-compat alias used by runtime factory and others
CaptureMode = ServingMode


@dataclass(frozen=True)
class Capture:
    """Unified capture configuration with simple, typed options.

    Modes are inferred by context:
    - Orchestrated runs default to batch semantics.
    - Serving defaults to realtime semantics.

    Options allow tuning behavior without exposing modes directly.
    """

    # If True, block at step end to publish updates (serving only).
    flush_on_step_end: bool | None = None
    # If True, pure in-memory execution (serving only).
    memory_only: bool = False
    # If False, skip doc/source capture in metadata.
    code: bool = True

    def to_config_value(self) -> Dict[str, Any]:
        """Convert the capture options to a config value.

        Returns:
            The config value (no explicit mode; inferred by environment).
        """
        cfg: Dict[str, Any] = {"code": self.code}
        if self.flush_on_step_end is not None:
            cfg["flush_on_step_end"] = bool(self.flush_on_step_end)
        if self.memory_only:
            cfg["memory_only"] = True
        return cfg


@dataclass(frozen=True)
class BatchCapture:
    """Batch (synchronous) capture configuration.

    Runs/steps and artifacts are always captured synchronously. Users should
    adjust logging/metadata/visualization via pipeline settings, not capture.
    """

    mode: ServingMode = ServingMode.BATCH

    def to_config_value(self) -> Dict[str, Any]:
        """Convert the batch capture to a config value."""
        return {"mode": self.mode.value}


@dataclass(frozen=True)
class RealtimeCapture:
    """Realtime capture configuration for serving.

    - flush_on_step_end: if True, block at step end to publish updates.
    - memory_only: if True, no server calls/runs/artifacts; in-process handoff.
    """

    mode: ServingMode = ServingMode.REALTIME
    flush_on_step_end: bool = False
    memory_only: bool = False

    def to_config_value(self) -> Dict[str, Any]:
        """Convert the realtime capture to a config value.

        Returns:
            The config value.
        """
        config: Dict[str, Any] = {"mode": self.mode.value}
        # Represent semantics using existing keys consumed by launcher/factory
        config["flush_on_step_end"] = self.flush_on_step_end
        if self.memory_only:
            config["memory_only"] = True
        return config

    def __post_init__(self) -> None:
        """Post init."""
        # Contradictory: memory-only implies no server operations to flush
        if self.memory_only and self.flush_on_step_end:
            raise ValueError(
                "Contradictory options: memory_only=True with flush_on_step_end=True. "
                "Memory-only mode has no server operations to flush."
            )


# Unified capture config type alias
CaptureConfig = Union[Capture, BatchCapture, RealtimeCapture]


class CapturePolicy:
    """Runtime-level capture policy used to select and configure runtimes.

    Provides a common interface for StepLauncher / factory code while the
    code-level API remains typed (`Capture`, `BatchCapture`, `RealtimeCapture`).
    """

    def __init__(
        self,
        mode: ServingMode = ServingMode.BATCH,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the capture policy.

        Args:
            mode: The mode to use.
            options: The options to use.
        """
        self.mode = mode
        self.options = options or {}

    @staticmethod
    def from_env() -> "CapturePolicy":
        """Create a capture policy from environment defaults.

        Returns:
            The capture policy.
        """
        if os.getenv("ZENML_SERVING_CAPTURE_DEFAULT") is not None:
            return CapturePolicy(mode=ServingMode.REALTIME, options={})
        val = os.getenv("ZENML_CAPTURE_MODE", "BATCH").upper()
        try:
            mode = ServingMode(val)
        except ValueError:
            mode = ServingMode.BATCH
        return CapturePolicy(mode=mode, options={})

    @staticmethod
    def from_value(
        value: Optional[Union[str, Capture, BatchCapture, RealtimeCapture]],
    ) -> "CapturePolicy":
        """Normalize typed or string capture value into a runtime policy.

        Args:
            value: The value to normalize.

        Returns:
            The capture policy.
        """
        if value is None:
            return CapturePolicy.from_env()

        if isinstance(value, RealtimeCapture):
            return CapturePolicy(
                mode=ServingMode.REALTIME,
                options={
                    "flush_on_step_end": value.flush_on_step_end,
                    "memory_only": bool(value.memory_only),
                },
            )
        if isinstance(value, BatchCapture):
            return CapturePolicy(mode=ServingMode.BATCH, options={})
        if isinstance(value, Capture):
            pol = CapturePolicy.from_env()
            opts: Dict[str, Any] = {}
            if value.flush_on_step_end is not None:
                opts["flush_on_step_end"] = bool(value.flush_on_step_end)
            if value.memory_only:
                opts["memory_only"] = True
            if value.code is not None:
                opts["code"] = bool(value.code)
            pol.options.update(opts)
            return pol
        # String fallback (YAML / ENV)
        try:
            return CapturePolicy(mode=ServingMode(str(value).upper()))
        except Exception:
            return CapturePolicy.from_env()

    def get_option(self, key: str, default: Any = None) -> Any:
        """Get an option from the capture policy.

        Args:
            key: The key to get.
            default: The default value to return if the key is not found.

        Returns:
            The option value.
        """
        return self.options.get(key, default)


# capture_to_config_value has been removed from code paths. Downstream consumers
# should use typed configs or CapturePolicy.from_value for YAML/ENV strings.
