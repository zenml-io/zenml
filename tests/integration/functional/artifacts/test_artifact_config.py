#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from typing import Tuple

from typing_extensions import Annotated

from zenml import pipeline, step
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.client import Client
from zenml.enums import ArtifactType, ModelStages
from zenml.model.model import Model

MODEL_NAME = "foo"


@step(model=Model(name=MODEL_NAME, version=ModelStages.LATEST))
def single_output_step_from_context() -> Annotated[int, ArtifactConfig()]:
    """Step that returns a single integer output.

    The output artifact is configured using `ArtifactConfig()` directly in the
    type annotation, linking it to the model version specified in the step's
    decorator.
    """
    return 1


@step(model=Model(name=MODEL_NAME, version=ModelStages.LATEST))
def single_output_step_from_context_model() -> Annotated[
    int, ArtifactConfig(artifact_type=ArtifactType.MODEL)
]:
    """Step that returns a single integer output, configured as a model artifact.

    The output artifact is explicitly typed as `ArtifactType.MODEL` using
    `ArtifactConfig` and linked to the model version from the step's context.
    """
    return 1


@step(model=Model(name=MODEL_NAME, version=ModelStages.LATEST))
def single_output_step_from_context_endpoint() -> Annotated[
    int, ArtifactConfig(artifact_type=ArtifactType.SERVICE)
]:
    """Step that returns a single integer output, configured as a service artifact.

    The output artifact is explicitly typed as `ArtifactType.SERVICE` (representing
    an endpoint/service) using `ArtifactConfig` and linked to the model version
    from the step's context.
    """
    return 1


@pipeline(enable_cache=False)
def simple_pipeline() -> None:
    """Defines a simple pipeline with three steps.

    The pipeline consists of three steps that each produce a single output.
    These outputs are configured to be linked as different artifact types
    (generic, model, and service) using `ArtifactConfig` within the step
    context. The steps run sequentially.
    """
    single_output_step_from_context()
    single_output_step_from_context_model(
        after=["single_output_step_from_context"]
    )
    single_output_step_from_context_endpoint(
        after=["single_output_step_from_context_model"]
    )


def test_link_minimalistic(clean_client: "Client") -> None:
    """Tests explicit artifact linking from step context for different artifact types.

    This test runs the `simple_pipeline`, which contains three steps each
    outputting an artifact. It verifies that these artifacts are correctly
    linked to the associated model version and that they have the specified
    artifact types (DATA, MODEL, SERVICE).

    Args:
        clean_client: A ZenML client instance.
    """
    # warm-up
    Model(name=MODEL_NAME)._get_or_create_model_version()

    simple_pipeline()

    mv = clean_client.get_model_version(MODEL_NAME, ModelStages.LATEST)
    assert mv.model.name == MODEL_NAME
    assert mv.number == 1 and mv.name == "1"
    links = clean_client.list_model_version_artifact_links(
        model_version_id=mv.id,
    )
    assert links.size == 3

    one_is_endpoint_artifact = False
    one_is_model_artifact = False
    one_is_data_artifact = False
    for link in links:
        one_is_endpoint_artifact ^= (
            link.artifact_version.type == ArtifactType.SERVICE
        )
        one_is_model_artifact ^= (
            link.artifact_version.type == ArtifactType.MODEL
        )
        one_is_data_artifact ^= link.artifact_version.type == ArtifactType.DATA
    assert one_is_endpoint_artifact
    assert one_is_model_artifact
    assert one_is_data_artifact


@step(model=Model(name=MODEL_NAME))
def multi_named_output_step_from_context() -> Tuple[
    Annotated[int, "1"],
    Annotated[int, "2"],
    Annotated[int, "3"],
]:
    """Step that returns three named integer outputs.

    Each output is annotated with a name ("1", "2", "3"). These artifacts
    will be linked to the model version specified in the step's decorator.
    """
    return 1, 2, 3


@pipeline(enable_cache=False)
def multi_named_pipeline() -> None:
    """Defines a pipeline that runs a single step with multiple named outputs.

    This pipeline utilizes the `multi_named_output_step_from_context` step,
    which produces three distinct, named outputs. The artifacts generated
    from these outputs are expected to be linked to the model version
    specified in the step's configuration.
    """
    multi_named_output_step_from_context()


def test_link_multiple_named_outputs(clean_client: "Client") -> None:
    """Tests artifact linking for a step that produces multiple named outputs.

    This test executes the `multi_named_pipeline`. It then verifies that all
    three named outputs from the `multi_named_output_step_from_context` step
    are correctly linked as artifacts to the corresponding model version.

    Args:
        clean_client: A ZenML client instance.
    """
    multi_named_pipeline()

    mv = clean_client.get_model_version(MODEL_NAME, ModelStages.LATEST)
    assert mv.model.name == MODEL_NAME
    assert mv.number == 1 and mv.name == "1"
    al = clean_client.list_model_version_artifact_links(
        model_version_id=mv.id,
    )
    assert al.size == 3


@step(model=Model(name=MODEL_NAME))
def multi_named_output_step_not_tracked() -> Tuple[
    Annotated[int, "1"],
    Annotated[int, "2"],
    Annotated[int, "3"],
]:
    """Step with multiple named outputs where artifact linking is implicit.

    The outputs "1", "2", and "3" are expected to be implicitly linked to the
    model version defined in the step's decorator, as no explicit
    `ArtifactConfig` is used.
    """
    return 1, 2, 3


@pipeline(enable_cache=False)
def multi_named_pipeline_not_tracked() -> None:
    """Defines a pipeline with a step that has multiple named outputs where artifact linking is implicit.

    This pipeline runs the `multi_named_output_step_not_tracked` step.
    The artifacts from this step are expected to be implicitly linked to the
    model version defined in the step's context, as no explicit
    `ArtifactConfig` is used for the outputs.
    """
    multi_named_output_step_not_tracked()


def test_link_multiple_named_outputs_without_links(clean_client: "Client") -> None:
    """Tests implicit artifact linking for a step with multiple named outputs.

    This test runs the `multi_named_pipeline_not_tracked`. It checks if the
    artifacts produced by the `multi_named_output_step_not_tracked` step are
    implicitly linked to the model version specified in the step's
    configuration, even without explicit `ArtifactConfig` in the output
    annotations.

    Args:
        clean_client: A ZenML client instance.
    """
    multi_named_pipeline_not_tracked()

    mv = clean_client.get_model_version(MODEL_NAME, ModelStages.LATEST)
    assert mv.number == 1 and mv.name == "1"
    assert mv.model.name == MODEL_NAME
    artifact_links = clean_client.list_model_version_artifact_links(
        model_version_id=mv.id,
    )
    assert artifact_links.size == 3


@step(model=Model(name="step", version="step"))
def multi_named_output_step_mixed_linkage() -> Tuple[
    Annotated[
        int,
        "2",
    ],
    Annotated[
        int,
        "3",
    ],
]:
    """Step with multiple named outputs ("2", "3") linked via step-level model context."""
    return 2, 3


@step
def pipeline_configuration_is_used_here() -> Tuple[
    Annotated[int, ArtifactConfig(name="custom_name")],
    Annotated[str, "4"],
]:
    """Step with two outputs demonstrating mixed artifact configuration.

    - The first output (integer) uses an explicit `ArtifactConfig` to set a
      custom artifact name "custom_name".
    - The second output (string, named "4") will be implicitly linked using the
      pipeline-level model context if available.
    """
    return 1, "foo"


@step
def some_plain_outputs() -> Tuple[str, float]:
    """Step returning a tuple of a string and a float.

    This output is expected to be treated as a single artifact (a tuple) and
    implicitly linked to the model version defined at the pipeline level.
    """
    return "bar", 42.0


@step(model=Model(name="step", version="step"))
def and_some_typed_outputs() -> int:
    """Step returning a single integer output.

    This artifact is expected to be implicitly linked to the model version
    defined in this step's decorator ("step/step").
    """
    return 1


@pipeline(
    enable_cache=False,
    model=Model(name="pipe", version="pipe"),
)
def multi_named_pipeline_mixed_linkage() -> None:
    """Defines a pipeline demonstrating mixed artifact linkage scenarios.

    This pipeline includes steps with various ways of defining artifact
    configurations:
    - `pipeline_configuration_is_used_here`: One output with custom ArtifactConfig,
      another implicitly linked via pipeline-level model.
    - `multi_named_output_step_mixed_linkage`: Outputs linked via step-level model.
    - `some_plain_outputs`: Output implicitly linked as a single tuple artifact
      via pipeline-level model.
    - `and_some_typed_outputs`: Output implicitly linked via step-level model.
    """
    pipeline_configuration_is_used_here()
    multi_named_output_step_mixed_linkage()
    some_plain_outputs()
    and_some_typed_outputs()


def test_link_multiple_named_outputs_with_mixed_linkage(
    clean_client: "Client",
) -> None:
    """Tests various scenarios of explicit and implicit artifact linking.

    This test executes the `multi_named_pipeline_mixed_linkage`. It verifies
    that artifacts from different steps, with mixed explicit `ArtifactConfig`
    and implicit model context linking (both step-level and pipeline-level),
    are correctly associated with their respective model versions.

    Args:
        clean_client: A ZenML client instance.
    """
    # manual creation needed, as we work with specific versions
    models = []
    mvs = []
    for n in ["pipe", "step"]:
        models.append(
            Model(
                name=n,
            )._get_or_create_model()
        )
        mvs.append(
            clean_client.create_model_version(
                name=n,
                model_name_or_id=models[-1].id,
            )
        )

    multi_named_pipeline_mixed_linkage()

    artifact_links = []
    for mv in mvs:
        artifact_links.append(
            clean_client.list_model_version_artifact_links(
                model_version_id=mv.id,
            )
        )

    assert artifact_links[0].size == 3
    assert artifact_links[1].size == 3


@step(enable_cache=True)
def _cacheable_step_annotated() -> Annotated[
    str, ArtifactConfig(name="cacheable", artifact_type=ArtifactType.MODEL)
]:
    """Cacheable step returning a string output explicitly configured as a model artifact named "cacheable"."""
    return "cacheable"


@step(enable_cache=True)
def _cacheable_step_not_annotated() -> str:
    """Cacheable step returning a string output with no explicit artifact configuration."""
    return "cacheable"


@step(enable_cache=False)
def _non_cacheable_step() -> str:
    """Non-cacheable step returning a string output."""
    return "not cacheable"


def test_artifacts_linked_from_cache_steps(clean_client: "Client") -> None:
    """Tests that artifacts are correctly linked to model versions even when steps are cached.

    This test defines and runs an inner pipeline (`_caching_test_pipeline`)
    multiple times. Some steps in this pipeline are cacheable. The test
    verifies that artifacts produced by these steps (whether from a cached run
    or a new execution) are correctly linked to the appropriate model version
    associated with each pipeline run.

    Args:
        clean_client: A ZenML client instance.
    """

    @pipeline(
        model=Model(name="foo"),
        enable_cache=False,
    )
    def _caching_test_pipeline(force_disable_cache: bool = False) -> None:
        """Pipeline to test artifact linking with cached steps.

        Contains a mix of cacheable and non-cacheable steps. Some cacheable
        steps have explicit ArtifactConfig, others don't.

        Args:
            force_disable_cache: If True, caching is disabled for normally
                cacheable steps in this run.
        """
        _cacheable_step_annotated.with_options(
            enable_cache=force_disable_cache
        )()
        _cacheable_step_not_annotated.with_options(
            enable_cache=force_disable_cache
        )()
        _non_cacheable_step()

    for i in range(1, 3):
        _caching_test_pipeline(i != 1)

        mvrm = clean_client.get_model_version(
            model_name_or_id="foo", model_version_name_or_number_or_id=i
        )
        assert len(mvrm.data_artifact_ids) == 2, f"Failed on {i} run"
        assert len(mvrm.model_artifact_ids) == 1, f"Failed on {i} run"
        assert set(mvrm.data_artifact_ids.keys()) == {
            "_caching_test_pipeline::_non_cacheable_step::output",
            "_caching_test_pipeline::_cacheable_step_not_annotated::output",
        }, f"Failed on {i} run"
        assert set(mvrm.model_artifact_ids.keys()) == {
            "cacheable",
        }, f"Failed on {i} run"


@step
def standard_name_producer() -> str:
    """Step that produces an artifact with a standard (default) name."""
    return "standard"


@step
def custom_name_producer() -> Annotated[
    str, "pipeline_::standard_name_producer::output"
]:
    """Step that produces an artifact with a custom name.

    The custom name is specified via `Annotated` and `ArtifactConfig` (implicitly,
    as a string is a valid shorthand for `ArtifactConfig(name=...)`).
    """
    return "custom"


def test_update_of_has_custom_name(clean_client: "Client") -> None:
    """Tests the behavior of the `has_custom_name` attribute of artifacts.

    This test verifies that the `has_custom_name` flag on an artifact is
    correctly set and persists:
    1. Initially False when an artifact is created with a standard name.
    2. True when an artifact (even if it's a new version of a previous one)
       is logged with a custom name via `ArtifactConfig`.
    3. Remains True even if a subsequent version of the same artifact is logged
       again with a standard (non-custom) name.

    Args:
        clean_client: A ZenML client instance.
    """

    @pipeline(enable_cache=False)
    def _standard_name_pipeline() -> None:
        """Pipeline that produces an artifact with a standard name."""
        standard_name_producer()

    @pipeline(enable_cache=False)
    def _custom_name_pipeline() -> None:
        """Pipeline that produces an artifact with a custom name."""
        custom_name_producer()

    # Run once -> no custom name
    _standard_name_pipeline()
    assert not clean_client.get_artifact(
        "_standard_name_pipeline::standard_name_producer::output"
    ).has_custom_name, "Standard name validation failed"

    # Run with custom name -> gets set to true
    _custom_name_pipeline()
    assert clean_client.get_artifact(
        "_standard_name_pipeline::standard_name_producer::output"
    ).has_custom_name, "Custom name validation failed"

    # Run again with standard name -> custom name stays true
    _standard_name_pipeline()
    assert clean_client.get_artifact(
        "_standard_name_pipeline::standard_name_producer::output"
    ).has_custom_name, "Custom name validation failed"

[end of tests/integration/functional/artifacts/test_artifact_config.py]
