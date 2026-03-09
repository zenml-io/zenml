from unittest.mock import Mock, patch
from uuid import uuid4

from zenml.artifacts.external_artifact_config import (
    ExternalArtifactConfiguration,
)
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.orchestrators.step_run_utils import StepRunRequestFactory


def _make_step(*, upstream_steps):
    step_spec = StepSpec.model_validate(
        {
            "source": "tests.unit.orchestrators.test_replay_input_overrides.step",
            "upstream_steps": upstream_steps,
            "inputs": {
                "input_": {
                    "step_name": "upstream",
                    "output_name": "output",
                }
            },
            "invocation_id": "consumer",
        }
    )
    step_config = StepConfiguration.model_validate({"name": "consumer"})
    return Step(
        spec=step_spec,
        config=step_config,
        step_config_overrides=step_config,
    )


def _make_factory(*, step):
    override_artifact_id = uuid4()
    pipeline_configuration = PipelineConfiguration(
        name="replay-pipeline",
        step_input_overrides={
            "consumer": {
                "input_": ExternalArtifactConfiguration(
                    id=override_artifact_id
                )
            }
        },
    )
    snapshot = Mock()
    snapshot.pipeline_configuration = pipeline_configuration
    snapshot.step_configurations = {"consumer": step}

    pipeline_run = Mock()
    pipeline_run.id = uuid4()
    pipeline_run.original_run = Mock(id=uuid4())

    stack = Mock()
    stack.artifact_store = Mock()

    factory = StepRunRequestFactory(
        snapshot=snapshot, pipeline_run=pipeline_run, stack=stack
    )
    return factory, override_artifact_id


def test_replay_input_override_is_applied():
    step = _make_step(upstream_steps=[])
    factory, override_artifact_id = _make_factory(step=step)

    original_step_run = Mock()
    original_step_run.inputs = {"input_": [Mock(id=uuid4())]}

    client_mock = Mock()
    client_mock.active_project.id = uuid4()
    client_mock.list_run_steps.return_value = [original_step_run]

    with (
        patch(
            "zenml.orchestrators.step_run_utils.Client",
            return_value=client_mock,
        ),
        patch.object(
            factory,
            "_get_docstring_and_source_code",
            return_value=(None, None),
        ),
        patch(
            "zenml.orchestrators.step_run_utils.cache_utils.generate_cache_key",
            return_value="cache-key",
        ),
        patch(
            "zenml.orchestrators.step_run_utils.input_utils.resolve_step_inputs"
        ) as resolve_step_inputs,
    ):
        request = factory.create_request("consumer")
        resolve_step_inputs.side_effect = (
            lambda step, pipeline_run, step_runs=None: {
                "input_": [
                    Mock(id=step.config.external_input_artifacts["input_"].id)
                ]
            }
        )

        factory.populate_request(request)

    assert request.inputs["input_"] == [override_artifact_id]


def test_replay_input_override_is_applied_with_upstream_steps():
    step = _make_step(upstream_steps=["upstream"])
    factory, override_artifact_id = _make_factory(step=step)

    original_step_run = Mock()
    original_step_run.inputs = {"input_": [Mock(id=uuid4())]}

    client_mock = Mock()
    client_mock.active_project.id = uuid4()
    client_mock.list_run_steps.return_value = [original_step_run]

    with (
        patch(
            "zenml.orchestrators.step_run_utils.Client",
            return_value=client_mock,
        ),
        patch.object(
            factory,
            "_get_docstring_and_source_code",
            return_value=(None, None),
        ),
        patch(
            "zenml.orchestrators.step_run_utils.cache_utils.generate_cache_key",
            return_value="cache-key",
        ),
        patch(
            "zenml.orchestrators.step_run_utils.input_utils.resolve_step_inputs"
        ) as resolve_step_inputs,
    ):
        request = factory.create_request("consumer")
        resolve_step_inputs.side_effect = (
            lambda step, pipeline_run, step_runs=None: {
                "input_": [
                    Mock(id=step.config.external_input_artifacts["input_"].id)
                ]
            }
        )

        factory.populate_request(request)

    assert request.inputs["input_"] == [override_artifact_id]
