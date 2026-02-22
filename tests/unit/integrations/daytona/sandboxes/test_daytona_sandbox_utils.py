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
"""Tests for Daytona sandbox helper utilities."""

from types import SimpleNamespace

from zenml.integrations.daytona.sandboxes.daytona_sandbox import (
    _extract_exit_code,
    _parse_gpu_count,
    _prepare_python_code,
    _resolve_auto_stop_interval,
    _split_lines,
)


def test_prepare_python_code_injects_inputs_prefix() -> None:
    """Tests code wrapping used to inject inputs into Python execution."""
    code = "output = x + y"

    prepared_code = _prepare_python_code(code=code, inputs={"x": 1, "y": 2})

    assert prepared_code.startswith("import json\n")
    assert "_zenml_inputs = json.loads" in prepared_code
    assert "globals().update(_zenml_inputs)" in prepared_code
    assert prepared_code.endswith(code)


def test_extract_exit_code_supports_aliases_and_invalid_values() -> None:
    """Tests extraction of exit codes from SDK-style payloads."""
    assert _extract_exit_code({"exitCode": "5"}) == 5
    assert _extract_exit_code(SimpleNamespace(return_code=7)) == 7
    assert _extract_exit_code({"exit_code": "not-a-number"}) is None
    assert _extract_exit_code({}) is None


def test_split_lines_preserves_newlines_and_handles_empty_input() -> None:
    """Tests newline-preserving split behavior for buffered output."""
    assert _split_lines("alpha\nbeta\n") == ["alpha\n", "beta\n"]
    assert _split_lines("") == []


def test_resolve_auto_stop_interval_applies_floor_and_scaling() -> None:
    """Tests safe auto-stop interval computation for session timeouts."""
    assert _resolve_auto_stop_interval(300) == 15
    assert _resolve_auto_stop_interval(3600) == 65


def test_parse_gpu_count_handles_numeric_and_invalid_values() -> None:
    """Tests parsing of generic GPU settings into Daytona GPU counts."""
    assert _parse_gpu_count("2") == 2
    assert _parse_gpu_count("2.0") == 2
    assert _parse_gpu_count(None) is None
    assert _parse_gpu_count("gpu") is None
