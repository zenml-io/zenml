import json
from typing import Any, Dict, List

from zenml.config.base_settings import BaseSettings
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.enums import StackComponentType
from zenml.zen_stores.template_utils import generate_config_schema


class _DummySettings(BaseSettings):
    pass


def _find_property_schemas(
    value: Any,
    property_name: str,
) -> List[Dict[str, Any]]:
    """Find all schemas for a given property name in a JSON schema."""
    matches: List[Dict[str, Any]] = []
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict) and property_name in properties:
            property_schema = properties[property_name]
            if isinstance(property_schema, dict):
                matches.append(property_schema)

        for nested_value in value.values():
            matches.extend(
                _find_property_schemas(
                    value=nested_value,
                    property_name=property_name,
                )
            )
    elif isinstance(value, list):
        for item in value:
            matches.extend(
                _find_property_schemas(
                    value=item,
                    property_name=property_name,
                )
            )

    return matches


def _allows_boolean(value: Any) -> bool:
    """Checks if a schema allows a boolean value."""
    if not isinstance(value, dict):
        return False

    if value.get("type") == "boolean":
        return True

    for key in ["anyOf", "oneOf", "allOf"]:
        options = value.get(key)
        if isinstance(options, list) and any(
            _allows_boolean(option) for option in options
        ):
            return True

    return False


def _has_enum_value(value: Any, enum_value: str) -> bool:
    """Checks if an enum value appears anywhere in a JSON schema."""
    if isinstance(value, dict):
        enum_values = value.get("enum")
        if isinstance(enum_values, list) and enum_value in enum_values:
            return True

        return any(
            _has_enum_value(nested_value, enum_value=enum_value)
            for nested_value in value.values()
        )
    elif isinstance(value, list):
        return any(
            _has_enum_value(item, enum_value=enum_value) for item in value
        )

    return False


def test_generate_config_schema_includes_sandbox_selector(mocker):
    """Tests that run template schemas include sandbox step selectors."""
    dummy_flavor = mocker.Mock()
    dummy_flavor.config_class = _DummySettings
    mocker.patch(
        "zenml.zen_stores.template_utils.Flavor.from_model",
        return_value=dummy_flavor,
    )

    flavor_schema = mocker.Mock()
    flavor_schema.to_model.return_value = mocker.Mock()

    sandbox_component = mocker.Mock(
        type=StackComponentType.SANDBOX,
        flavor="modal",
        flavor_schema=flavor_schema,
    )
    sandbox_component.name = "my-sandbox"

    stack = mocker.Mock(components=[sandbox_component])
    snapshot = mocker.Mock(build=mocker.Mock(stack=stack), is_dynamic=False)

    step = mocker.Mock()
    step.config = mocker.Mock(parameters={})

    schema = generate_config_schema(
        snapshot=snapshot,
        pipeline_configuration=PipelineConfiguration(name="test_pipeline"),
        step_configurations={"test_step": step},
    )

    assert "sandbox" in json.dumps(schema)

    sandbox_property_schemas = _find_property_schemas(
        value=schema,
        property_name="sandbox",
    )
    assert sandbox_property_schemas
    assert any(
        _allows_boolean(field_schema)
        for field_schema in sandbox_property_schemas
    )
    assert _has_enum_value(schema, enum_value="my-sandbox")
