from types import SimpleNamespace
from typing import Any, Dict

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.zen_stores.template_utils import generate_config_schema


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


def test_generate_config_schema_with_parameter_spec_and_no_config_parameters():
    """Schema generation must not crash when a step carries a
    `parameter_spec` without matching `config.parameters`.

    The step-level `{step_name}_parameters` `$def` is only created when
    `step.config.parameters` is truthy. A step whose spec was loaded from
    a stored snapshot (for example when regenerating a config schema from
    an existing template) may expose a `parameter_spec` while having an
    empty `config.parameters`; the schema substitution path must handle
    that case gracefully instead of raising `KeyError`.
    """
    step = Step(
        spec=StepSpec(
            source="module.step",
            upstream_steps=[],
            invocation_id="my_step",
            parameter_spec={
                "type": "object",
                "properties": {"a": {"type": "integer"}},
                "required": ["a"],
            },
        ),
        config=StepConfiguration(name="my_step", parameters={}),
        step_config_overrides=StepConfiguration(
            name="my_step", parameters={}
        ),
    )
    snapshot = SimpleNamespace(
        is_dynamic=False,
        build=SimpleNamespace(stack=SimpleNamespace(components=[])),
    )

    # Must not raise `KeyError('my_step_parameters')`.
    schema = generate_config_schema(
        snapshot=snapshot,
        pipeline_configuration=PipelineConfiguration(name="pipeline"),
        step_configurations={"my_step": step},
    )

    assert "$defs" in schema
