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
"""Tests for Monty sandbox helper utilities."""

import pytest

from zenml.integrations.monty.sandboxes.monty_sandbox import (
    _format_monty_error,
    _merge_type_check_stubs,
    _render_input_assignments,
    _serialize_output,
)


class _DisplayError(Exception):
    """Exception that exposes a `display` method used by Monty helpers."""

    def display(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Renders rich output for supported display call signatures."""
        if args == ("full",):
            raise TypeError("Old display signature is unsupported")
        if kwargs == {"format": "full"}:
            return "formatted-from-format-kwarg"
        return "formatted-default"


class _BrokenDisplayError(Exception):
    """Exception whose display method fails and should fall back to str()."""

    def display(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Raises runtime errors to force fallback behavior."""
        raise RuntimeError("display failed")


def test_render_input_assignments_returns_python_assignment_lines() -> None:
    """Tests assignment rendering for valid Monty input keys."""
    rendered = _render_input_assignments({"alpha": 1, "beta": "x"})

    assert rendered.splitlines() == ["alpha = 1", "beta = 'x'"]


def test_render_input_assignments_rejects_invalid_identifier() -> None:
    """Tests validation of identifier names used as injected variables."""
    with pytest.raises(ValueError, match="not a valid Python identifier"):
        _render_input_assignments({"invalid-key": 1})


def test_merge_type_check_stubs_appends_only_valid_input_names() -> None:
    """Tests that generated stubs include only identifier-safe input names."""
    merged = _merge_type_check_stubs(
        base_stubs="from typing import Any\nexisting: Any",
        input_names=["alpha", "invalid-key", "beta"],
    )

    assert merged is not None
    assert "existing: Any" in merged
    assert "alpha: Any" in merged
    assert "beta: Any" in merged
    assert "invalid-key" not in merged


def test_serialize_output_handles_json_and_non_json_values() -> None:
    """Tests serialization behavior at the sandbox JSON boundary."""
    assert _serialize_output({"key": "value"}) == {"key": "value"}
    assert _serialize_output(None) is None

    class _NonJson:
        pass

    serialized = _serialize_output(_NonJson())
    assert serialized is not None
    assert serialized.startswith("<")


def test_format_monty_error_prefers_display_then_falls_back_to_str() -> None:
    """Tests rich error rendering fallback order."""
    assert _format_monty_error(_DisplayError("boom")) == (
        "formatted-from-format-kwarg"
    )
    assert _format_monty_error(_BrokenDisplayError("plain-error")) == (
        "plain-error"
    )
