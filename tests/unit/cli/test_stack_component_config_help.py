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
"""Tests for stack component register/update/remove-attribute --help flavor schema."""

import pytest

from tests.cli_runner_utils import cli_runner
from zenml.cli.cli import cli
from zenml.cli.utils import _resolve_schema_property_type, _type_to_metavar
from zenml.enums import StackComponentType


def _make_mock_client(config_schema, component_flavor="default"):
    """Build a mock Client class that returns a flavor with the given schema."""

    class _MockClient:
        def get_flavor_by_name_and_type(
            self, name: str, component_type: StackComponentType
        ) -> object:
            class _Flavor:
                pass

            f = _Flavor()
            f.config_schema = config_schema
            return f

        def get_stack_component(
            self, name_id_or_prefix: str, component_type: StackComponentType
        ) -> object:
            class _ComponentFlavor:
                pass

            cf = _ComponentFlavor()
            cf.config_schema = config_schema

            class _Component:
                pass

            c = _Component()
            c.flavor_name = component_flavor
            c.flavor = cf
            return c

    return _MockClient


def test_register_help_includes_flavor_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flavor config schema is appended when ``-f`` is present."""
    schema = {
        "title": "TestFlavorConfig",
        "properties": {
            "uri": {
                "type": "string",
                "description": "Endpoint URI.",
            }
        },
    }
    monkeypatch.setattr(
        "zenml.cli.stack_components.Client", _make_mock_client(schema)
    )

    runner = cli_runner()
    result = runner.invoke(
        cli,
        ["orchestrator", "register", "-f", "default", "--help"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Flavor configuration" in result.output
    assert "--uri TEXT" in result.output
    assert "Endpoint URI." in result.output
    assert "Pass each field as `--name=value`" in result.output


def test_register_help_works_with_extra_config_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Schema shows even when unknown config args are present alongside -f."""
    schema = {
        "title": "TestFlavorConfig",
        "properties": {
            "uri": {
                "type": "string",
                "description": "Endpoint URI.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds.",
            },
        },
    }
    monkeypatch.setattr(
        "zenml.cli.stack_components.Client", _make_mock_client(schema)
    )

    runner = cli_runner()
    result = runner.invoke(
        cli,
        [
            "orchestrator",
            "register",
            "my-orch",
            "-f",
            "default",
            "--uri=http://localhost",
            "--timeout=30",
            "--help",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Flavor configuration" in result.output
    assert "--uri TEXT" in result.output
    assert "--timeout INTEGER" in result.output


def test_update_help_includes_flavor_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flavor config schema is appended when the component name is present."""
    schema = {
        "title": "UpdateFlavorConfig",
        "properties": {
            "sync": {
                "type": "boolean",
                "description": "Whether to sync.",
            }
        },
    }
    monkeypatch.setattr(
        "zenml.cli.stack_components.Client", _make_mock_client(schema)
    )

    runner = cli_runner()
    result = runner.invoke(
        cli,
        ["orchestrator", "update", "my-orch", "--help"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Flavor configuration" in result.output
    assert "--sync BOOLEAN" in result.output


def test_register_help_without_flavor_has_no_schema_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No flavor means no schema block."""
    monkeypatch.setattr(
        "zenml.cli.stack_components.Client",
        _make_mock_client({"properties": {}}),
    )

    runner = cli_runner()
    result = runner.invoke(
        cli,
        ["orchestrator", "register", "--help"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Flavor configuration" not in result.output


def test_register_help_shows_required_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Required fields are annotated with [required]."""
    schema = {
        "title": "TestConfig",
        "required": ["endpoint"],
        "properties": {
            "endpoint": {
                "type": "string",
                "description": "API endpoint.",
            },
            "optional_field": {
                "type": "string",
                "description": "Not required.",
            },
        },
    }
    monkeypatch.setattr(
        "zenml.cli.stack_components.Client", _make_mock_client(schema)
    )

    runner = cli_runner()
    result = runner.invoke(
        cli,
        ["orchestrator", "register", "-f", "default", "--help"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "[required]" in result.output
    assert "API endpoint." in result.output
    assert "Not required." in result.output


def test_register_help_skips_ref_properties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Properties with $ref (complex nested objects) are skipped."""
    schema = {
        "title": "TestConfig",
        "properties": {
            "name": {"type": "string", "description": "Name."},
            "nested": {"$ref": "#/definitions/SomeModel"},
        },
    }
    monkeypatch.setattr(
        "zenml.cli.stack_components.Client", _make_mock_client(schema)
    )

    runner = cli_runner()
    result = runner.invoke(
        cli,
        ["orchestrator", "register", "-f", "default", "--help"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "--name TEXT" in result.output
    assert "--nested" not in result.output


# -- Unit tests for schema type resolution and metavar mapping --


class TestResolveSchemaPropertyType:
    """Tests for _resolve_schema_property_type."""

    def test_string(self) -> None:
        assert _resolve_schema_property_type({"type": "string"}) == "string"

    def test_boolean(self) -> None:
        assert _resolve_schema_property_type({"type": "boolean"}) == "boolean"

    def test_integer(self) -> None:
        assert _resolve_schema_property_type({"type": "integer"}) == "integer"

    def test_number(self) -> None:
        assert _resolve_schema_property_type({"type": "number"}) == "number"

    def test_array(self) -> None:
        assert _resolve_schema_property_type({"type": "array"}) == "array"

    def test_object(self) -> None:
        assert _resolve_schema_property_type({"type": "object"}) == "object"

    def test_anyof_nullable_string(self) -> None:
        schema = {"anyOf": [{"type": "string"}, {"type": "null"}]}
        assert _resolve_schema_property_type(schema) == "string"

    def test_anyof_nullable_integer(self) -> None:
        schema = {"anyOf": [{"type": "integer"}, {"type": "null"}]}
        assert _resolve_schema_property_type(schema) == "integer"

    def test_enum_without_type(self) -> None:
        assert (
            _resolve_schema_property_type({"enum": ["cpu", "gpu"]}) == "string"
        )

    def test_enum_with_type_prefers_type(self) -> None:
        schema = {"type": "string", "enum": ["cpu", "gpu"]}
        assert _resolve_schema_property_type(schema) == "string"

    def test_anyof_only_null_falls_back(self) -> None:
        assert (
            _resolve_schema_property_type({"anyOf": [{"type": "null"}]})
            == "object"
        )

    def test_unknown_defaults_to_object(self) -> None:
        assert _resolve_schema_property_type({}) == "object"


class TestTypeToMetavar:
    """Tests for _type_to_metavar."""

    def test_known_types(self) -> None:
        assert _type_to_metavar("string") == "TEXT"
        assert _type_to_metavar("boolean") == "BOOLEAN"
        assert _type_to_metavar("integer") == "INTEGER"
        assert _type_to_metavar("number") == "NUMBER"
        assert _type_to_metavar("array") == "LIST"
        assert _type_to_metavar("object") == "JSON"

    def test_unknown_defaults_to_text(self) -> None:
        assert _type_to_metavar("custom") == "TEXT"


def test_remove_attribute_help_includes_flavor_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flavor config schema is appended for remove-attribute when name is present."""
    schema = {
        "title": "RemoveAttrFlavorConfig",
        "properties": {
            "uri": {
                "type": "string",
                "description": "Endpoint URI.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds.",
            },
        },
    }
    monkeypatch.setattr(
        "zenml.cli.stack_components.Client", _make_mock_client(schema)
    )

    runner = cli_runner()
    result = runner.invoke(
        cli,
        ["orchestrator", "remove-attribute", "my-orch", "--help"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Flavor configuration" in result.output
    assert "--uri TEXT" in result.output
    assert "--timeout INTEGER" in result.output
    assert "Pass each field name as a positional ARGS" in result.output


def test_remove_attribute_help_without_name_has_no_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No component name means no schema block."""
    monkeypatch.setattr(
        "zenml.cli.stack_components.Client",
        _make_mock_client({"properties": {}}),
    )

    runner = cli_runner()
    result = runner.invoke(
        cli,
        ["orchestrator", "remove-attribute", "--help"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Flavor configuration" not in result.output
