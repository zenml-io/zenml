"""Tests for run template utilities."""

from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import Mock, patch

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import StackComponentType
from zenml.zen_stores.template_utils import (
    generate_config_schema,
    generate_config_template,
)


def _create_step(name: str, parameter_spec: Dict[str, Any]) -> Step:
    """Create a step.

    Args:
        name: The step name.
        parameter_spec: The step parameter schema.

    Returns:
        A step.
    """
    return Step(
        spec=StepSpec(
            source="module.step",
            upstream_steps=[],
            invocation_id=name,
            parameter_spec=parameter_spec,
        ),
        config=StepConfiguration(
            name=name, parameters={"config": {"value": 1}}
        ),
        step_config_overrides=StepConfiguration(
            name=name, parameters={"config": {"value": 1}}
        ),
    )


def test_generate_config_schema_embeds_step_parameter_schema():
    """Tests that step parameter schemas are embedded into step schemas."""
    step = _create_step(
        "my_step",
        {
            "type": "object",
            "properties": {"a": {"type": "integer"}},
            "required": ["a"],
        },
    )
    snapshot = SimpleNamespace(
        is_dynamic=False,
        build=SimpleNamespace(stack=SimpleNamespace(components=[])),
    )

    schema = generate_config_schema(
        snapshot=snapshot,
        pipeline_configuration=PipelineConfiguration(name="pipeline"),
        step_configurations={"my_step": step},
    )

    assert schema["$defs"]["my_step"]["properties"]["parameters"] == {
        "type": "object",
        "properties": {"a": {"type": "integer"}},
        "required": ["a"],
    }


def test_generate_config_schema_reuses_and_renames_step_defs():
    """Tests that identical defs are reused and conflicting defs are renamed."""
    shared_definition = {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
    }
    conflicting_definition = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    }
    snapshot = SimpleNamespace(
        is_dynamic=False,
        build=SimpleNamespace(stack=SimpleNamespace(components=[])),
    )

    schema = generate_config_schema(
        snapshot=snapshot,
        pipeline_configuration=PipelineConfiguration(name="pipeline"),
        step_configurations={
            "shared_step_0": _create_step(
                "shared_step_0",
                {
                    "type": "object",
                    "properties": {"config": {"$ref": "#/$defs/NestedConfig"}},
                    "required": ["config"],
                    "$defs": {"NestedConfig": shared_definition},
                },
            ),
            "shared_step_1": _create_step(
                "shared_step_1",
                {
                    "type": "object",
                    "properties": {"config": {"$ref": "#/$defs/NestedConfig"}},
                    "required": ["config"],
                    "$defs": {"NestedConfig": shared_definition},
                },
            ),
            "conflicting_step": _create_step(
                "conflicting_step",
                {
                    "type": "object",
                    "properties": {"config": {"$ref": "#/$defs/NestedConfig"}},
                    "required": ["config"],
                    "$defs": {"NestedConfig": conflicting_definition},
                },
            ),
        },
    )

    assert schema["$defs"]["NestedConfig"] == shared_definition
    assert (
        schema["$defs"]["shared_step_0"]["properties"]["parameters"][
            "properties"
        ]["config"]["$ref"]
        == "#/$defs/NestedConfig"
    )
    assert (
        schema["$defs"]["shared_step_1"]["properties"]["parameters"][
            "properties"
        ]["config"]["$ref"]
        == "#/$defs/NestedConfig"
    )
    assert (
        schema["$defs"]["conflicting_step__NestedConfig"]
        == conflicting_definition
    )
    assert (
        schema["$defs"]["conflicting_step"]["properties"]["parameters"][
            "properties"
        ]["config"]["$ref"]
        == "#/$defs/conflicting_step__NestedConfig"
    )


def test_generate_config_schema_does_not_import_custom_flavors():
    """Tests that custom flavors are not imported for schema generation."""
    flavor_schema = Mock(is_custom=True)
    component = SimpleNamespace(
        name="custom_step_operator",
        type=StackComponentType.STEP_OPERATOR,
        flavor_schema=flavor_schema,
    )
    snapshot = SimpleNamespace(
        is_dynamic=False,
        build=SimpleNamespace(stack=SimpleNamespace(components=[component])),
    )

    with patch(
        "zenml.zen_stores.template_utils.Flavor.from_model"
    ) as from_model:
        schema = generate_config_schema(
            snapshot=snapshot,
            pipeline_configuration=PipelineConfiguration(name="pipeline"),
            step_configurations={"my_step": _create_step("my_step", {})},
        )

    flavor_schema.to_model.assert_not_called()
    from_model.assert_not_called()
    assert schema["$defs"]["StepOperators"]["enum"] == ["custom_step_operator"]


def test_generate_config_template_serializes_hook_sources_as_import_paths():
    """Tests that hook sources are stringified in generated templates."""
    step = Step(
        spec=StepSpec(
            source="module.step",
            upstream_steps=[],
            invocation_id="my_step",
        ),
        config=StepConfiguration(name="my_step"),
        step_config_overrides=StepConfiguration(
            name="my_step",
            failure_hook_source="hooks.step_failure",
            success_hook_source="hooks.step_success",
        ),
    )
    snapshot = SimpleNamespace(is_dynamic=True, run_name_template="my_run")

    template = generate_config_template(
        snapshot=snapshot,
        pipeline_configuration=PipelineConfiguration(
            name="pipeline",
            failure_hook_source="hooks.pipeline_failure",
            success_hook_source="hooks.pipeline_success",
            init_hook_source="hooks.pipeline_init",
            cleanup_hook_source="hooks.pipeline_cleanup",
        ),
        step_configurations={"my_step": step},
    )

    assert template["failure_hook_source"] == "hooks.pipeline_failure"
    assert template["success_hook_source"] == "hooks.pipeline_success"
    assert template["init_hook_source"] == "hooks.pipeline_init"
    assert template["cleanup_hook_source"] == "hooks.pipeline_cleanup"
    assert (
        template["steps"]["my_step"]["failure_hook_source"]
        == "hooks.step_failure"
    )
    assert (
        template["steps"]["my_step"]["success_hook_source"]
        == "hooks.step_success"
    )
