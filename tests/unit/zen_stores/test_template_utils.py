from types import SimpleNamespace

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.zen_stores.template_utils import generate_config_schema


def _create_step(name: str, parameter_spec: dict) -> Step:
    """Creates a step for template schema tests.

    Args:
        name: The step name.
        parameter_spec: The step parameter schema.

    Returns:
        A test step.
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
            "trainer": _create_step(
                "trainer",
                {
                    "type": "object",
                    "properties": {"config": {"$ref": "#/$defs/NestedConfig"}},
                    "required": ["config"],
                    "$defs": {"NestedConfig": shared_definition},
                },
            ),
            "evaluator": _create_step(
                "evaluator",
                {
                    "type": "object",
                    "properties": {"config": {"$ref": "#/$defs/NestedConfig"}},
                    "required": ["config"],
                    "$defs": {"NestedConfig": shared_definition},
                },
            ),
            "deployer": _create_step(
                "deployer",
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
        schema["$defs"]["trainer"]["properties"]["parameters"]["properties"][
            "config"
        ]["$ref"]
        == "#/$defs/NestedConfig"
    )
    assert (
        schema["$defs"]["evaluator"]["properties"]["parameters"]["properties"][
            "config"
        ]["$ref"]
        == "#/$defs/NestedConfig"
    )
    assert schema["$defs"]["deployer__NestedConfig"] == conflicting_definition
    assert (
        schema["$defs"]["deployer"]["properties"]["parameters"]["properties"][
            "config"
        ]["$ref"]
        == "#/$defs/deployer__NestedConfig"
    )
