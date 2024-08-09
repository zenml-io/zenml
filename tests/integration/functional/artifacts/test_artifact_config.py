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
from zenml.enums import ModelStages
from zenml.model.model import Model

MODEL_NAME = "foo"


@step(model=Model(name=MODEL_NAME, version=ModelStages.LATEST))
def single_output_step_from_context() -> Annotated[int, ArtifactConfig()]:
    """Untyped single output linked as Artifact from step context."""
    return 1


@step(model=Model(name=MODEL_NAME, version=ModelStages.LATEST))
def single_output_step_from_context_model() -> (
    Annotated[int, ArtifactConfig(is_model_artifact=True)]
):
    """Untyped single output linked as a model artifact from step context."""
    return 1


@step(model=Model(name=MODEL_NAME, version=ModelStages.LATEST))
def single_output_step_from_context_endpoint() -> (
    Annotated[int, ArtifactConfig(is_deployment_artifact=True)]
):
    """Untyped single output linked as endpoint artifact from step context."""
    return 1


@pipeline(enable_cache=False)
def simple_pipeline():
    """Run 3 untyped single output linked from step context."""
    single_output_step_from_context()
    single_output_step_from_context_model(
        after=["single_output_step_from_context"]
    )
    single_output_step_from_context_endpoint(
        after=["single_output_step_from_context_model"]
    )


def test_link_minimalistic(clean_client: "Client"):
    """Test simple explicit linking from step context for 3 artifact types."""
    user = clean_client.active_user.id
    ws = clean_client.active_workspace.id

    # warm-up
    Model(name=MODEL_NAME)._get_or_create_model_version()

    simple_pipeline()

    mv = clean_client.get_model_version(MODEL_NAME, ModelStages.LATEST)
    assert mv.model.name == MODEL_NAME
    assert mv.number == 1 and mv.name == "1"
    links = clean_client.list_model_version_artifact_links(
        model_version_id=mv.id,
        user_id=user,
        workspace_id=ws,
    )
    assert links.size == 3

    one_is_endpoint_artifact = False
    one_is_model_artifact = False
    one_is_data_artifact = False
    for link in links:
        one_is_endpoint_artifact ^= (
            link.is_deployment_artifact and not link.is_model_artifact
        )
        one_is_model_artifact ^= (
            not link.is_deployment_artifact and link.is_model_artifact
        )
        one_is_data_artifact ^= (
            not link.is_deployment_artifact and not link.is_model_artifact
        )
    assert one_is_endpoint_artifact
    assert one_is_model_artifact
    assert one_is_data_artifact


@step(model=Model(name=MODEL_NAME))
def multi_named_output_step_from_context() -> (
    Tuple[
        Annotated[int, "1"],
        Annotated[int, "2"],
        Annotated[int, "3"],
    ]
):
    """3 typed output step with explicit linking from step context."""
    return 1, 2, 3


@pipeline(enable_cache=False)
def multi_named_pipeline():
    """3 typed output step with explicit linking from step context."""
    multi_named_output_step_from_context()


def test_link_multiple_named_outputs(clean_client: "Client"):
    """Test multiple typed output step with explicit linking from step context."""
    user = clean_client.active_user.id
    ws = clean_client.active_workspace.id

    multi_named_pipeline()

    mv = clean_client.get_model_version(MODEL_NAME, ModelStages.LATEST)
    assert mv.model.name == MODEL_NAME
    assert mv.number == 1 and mv.name == "1"
    al = clean_client.list_model_version_artifact_links(
        model_version_id=mv.id,
        user_id=user,
        workspace_id=ws,
    )
    assert al.size == 3


@step(model=Model(name=MODEL_NAME))
def multi_named_output_step_not_tracked() -> (
    Tuple[
        Annotated[int, "1"],
        Annotated[int, "2"],
        Annotated[int, "3"],
    ]
):
    """Here links would be implicitly created based on step Model."""
    return 1, 2, 3


@pipeline(enable_cache=False)
def multi_named_pipeline_not_tracked():
    """Here links would be implicitly created based on step Model."""
    multi_named_output_step_not_tracked()


def test_link_multiple_named_outputs_without_links(clean_client: "Client"):
    """Test multi output step implicit linking based on step context."""
    user = clean_client.active_user.id
    ws = clean_client.active_workspace.id

    multi_named_pipeline_not_tracked()

    mv = clean_client.get_model_version(MODEL_NAME, ModelStages.LATEST)
    assert mv.number == 1 and mv.name == "1"
    assert mv.model.name == MODEL_NAME
    artifact_links = clean_client.list_model_version_artifact_links(
        model_version_id=mv.id,
        user_id=user,
        workspace_id=ws,
    )
    assert artifact_links.size == 3


@step
def multi_named_output_step_from_self() -> (
    Tuple[
        Annotated[
            int,
            "1",
            ArtifactConfig(model_name=MODEL_NAME, model_version="bar"),
        ],
        Annotated[
            int,
            "2",
            ArtifactConfig(model_name=MODEL_NAME, model_version="bar"),
        ],
        Annotated[
            int,
            "3",
            ArtifactConfig(model_name="bar", model_version="foo"),
        ],
    ]
):
    """Multi output linking from Annotated."""
    return 1, 2, 3


@pipeline
def multi_named_pipeline_from_self(enable_cache: bool):
    """Multi output linking from Annotated."""
    multi_named_output_step_from_self.with_options(enable_cache=enable_cache)()


def test_link_multiple_named_outputs_with_self_context_and_caching(
    clean_client: "Client",
):
    """Test multi output linking with context defined in Annotated."""
    user = clean_client.active_user.id
    ws = clean_client.active_workspace.id

    # manual creation needed, as we work with specific versions
    m1 = Model(
        name=MODEL_NAME,
    )._get_or_create_model()
    m2 = Model(
        name="bar",
    )._get_or_create_model()

    mv1 = clean_client.create_model_version(
        name="bar",
        model_name_or_id=m1.id,
    )
    mv2 = clean_client.create_model_version(
        name="foo",
        model_name_or_id=m2.id,
    )

    for run_count in range(1, 3):
        multi_named_pipeline_from_self(run_count == 2)

        al1 = clean_client.list_model_version_artifact_links(
            model_version_id=mv1.id,
            user_id=user,
            workspace_id=ws,
        )
        al2 = clean_client.list_model_version_artifact_links(
            model_version_id=mv2.id,
            user_id=user,
            workspace_id=ws,
        )
        assert al1.size == 2, f"Failed on {run_count} run"
        assert al2.size == 1, f"Failed on {run_count} run"

        # clean-up links to test caching linkage
        for mv, al in zip([mv1, mv2], [al1, al2]):
            for al_ in al:
                clean_client.zen_store.delete_model_version_artifact_link(
                    model_version_id=mv.id,
                    model_version_artifact_link_name_or_id=al_.id,
                )


@step(model=Model(name="step", version="step"))
def multi_named_output_step_mixed_linkage() -> (
    Tuple[
        Annotated[
            int,
            "2",
        ],
        Annotated[
            int,
            "3",
            ArtifactConfig(model_name="artifact", model_version="artifact"),
        ],
    ]
):
    """Artifact 2 will get step context and 3 defines own."""
    return 2, 3


@step
def pipeline_configuration_is_used_here() -> (
    Tuple[
        Annotated[int, ArtifactConfig(name="custom_name")],
        Annotated[str, "4"],
    ]
):
    """Artifact "1" has own config and overrides name, but "4" will be implicitly tracked with pipeline config."""
    return 1, "foo"


@step
def some_plain_outputs():
    """This artifact will be implicitly tracked with pipeline config as a single tuple."""
    return "bar", 42.0


@step(model=Model(name="step", version="step"))
def and_some_typed_outputs() -> int:
    """This artifact can be implicitly tracked with step config."""
    return 1


@pipeline(
    enable_cache=False,
    model=Model(name="pipe", version="pipe"),
)
def multi_named_pipeline_mixed_linkage():
    """Mixed linking cases, see steps description."""
    pipeline_configuration_is_used_here()
    multi_named_output_step_mixed_linkage()
    some_plain_outputs()
    and_some_typed_outputs()


def test_link_multiple_named_outputs_with_mixed_linkage(
    clean_client: "Client",
):
    """In this test a mixed linkage of artifacts is verified. See steps description."""
    user = clean_client.active_user.id
    ws = clean_client.active_workspace.id

    # manual creation needed, as we work with specific versions
    models = []
    mvs = []
    for n in ["pipe", "step", "artifact"]:
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
                user_id=user,
                workspace_id=ws,
            )
        )

    assert artifact_links[0].size == 3
    assert artifact_links[1].size == 2
    assert artifact_links[2].size == 1


@step(enable_cache=True)
def _cacheable_step_annotated() -> (
    Annotated[str, ArtifactConfig(name="cacheable", is_model_artifact=True)]
):
    return "cacheable"


@step(enable_cache=True)
def _cacheable_step_not_annotated():
    return "cacheable"


@step(enable_cache=True)
def _cacheable_step_custom_model_annotated() -> (
    Annotated[
        str,
        "cacheable",
        ArtifactConfig(model_name="bar", model_version=ModelStages.LATEST),
    ]
):
    return "cacheable"


@step(enable_cache=False)
def _non_cacheable_step():
    return "not cacheable"


def test_artifacts_linked_from_cache_steps(clean_client: "Client"):
    """Test that artifacts are linked from cache steps."""

    @pipeline(
        model=Model(name="foo"),
        enable_cache=False,
    )
    def _inner_pipeline(force_disable_cache: bool = False):
        _cacheable_step_annotated.with_options(
            enable_cache=force_disable_cache
        )()
        _cacheable_step_not_annotated.with_options(
            enable_cache=force_disable_cache
        )()
        _cacheable_step_custom_model_annotated.with_options(
            enable_cache=force_disable_cache
        )()
        _non_cacheable_step()

    for i in range(1, 3):
        Model(name="bar")._get_or_create_model_version()
        _inner_pipeline(i != 1)

        mvrm = clean_client.get_model_version(
            model_name_or_id="foo", model_version_name_or_number_or_id=i
        )
        assert len(mvrm.data_artifact_ids) == 2, f"Failed on {i} run"
        assert len(mvrm.model_artifact_ids) == 1, f"Failed on {i} run"
        assert set(mvrm.data_artifact_ids.keys()) == {
            "_inner_pipeline::_non_cacheable_step::output",
            "_inner_pipeline::_cacheable_step_not_annotated::output",
        }, f"Failed on {i} run"
        assert set(mvrm.model_artifact_ids.keys()) == {
            "cacheable",
        }, f"Failed on {i} run"

        mvrm = clean_client.get_model_version(model_name_or_id="bar")

        assert len(mvrm.data_artifact_ids) == 1, f"Failed on {i} run"
        assert set(mvrm.data_artifact_ids.keys()) == {
            "cacheable",
        }, f"Failed on {i} run"
        assert (
            len(mvrm.data_artifact_ids["cacheable"]) == 1
        ), f"Failed on {i} run"


def test_artifacts_linked_from_cache_steps_same_id(clean_client: "Client"):
    """Test that artifacts are linked from cache steps with same id.
    This case appears if cached step is executed inside same model version,
    and we need to silently pass linkage without failing on same id.
    """

    @pipeline(
        model=Model(name="foo"),
        enable_cache=False,
    )
    def _inner_pipeline(force_disable_cache: bool = False):
        _cacheable_step_custom_model_annotated.with_options(
            enable_cache=force_disable_cache
        )()
        _non_cacheable_step()

    for i in range(1, 3):
        Model(name="bar")._get_or_create_model_version()
        _inner_pipeline(i != 1)

        mvrm = clean_client.get_model_version(
            model_name_or_id="bar",
        )
        assert len(mvrm.data_artifact_ids) == 1, f"Failed on {i} run"
        assert set(mvrm.data_artifact_ids.keys()) == {
            "cacheable",
        }, f"Failed on {i} run"
        assert (
            len(mvrm.data_artifact_ids["cacheable"]) == 1
        ), f"Failed on {i} run"


@step
def standard_name_producer() -> str:
    return "standard"


@step
def custom_name_producer() -> (
    Annotated[str, "pipeline_::standard_name_producer::output"]
):
    return "custom"


def test_update_of_has_custom_name(clean_client: "Client"):
    """Test that update of has_custom_name works."""

    @pipeline(enable_cache=False)
    def pipeline_():
        standard_name_producer()

    @pipeline(enable_cache=False)
    def pipeline_2():
        custom_name_producer()

    # run 2 times to see both ways switching
    for i in range(2):
        pipeline_()
        assert not clean_client.get_artifact(
            "pipeline_::standard_name_producer::output"
        ).has_custom_name, f"Standard name validation failed in {i+1} run"

        pipeline_2()
        assert clean_client.get_artifact(
            "pipeline_::standard_name_producer::output"
        ).has_custom_name, f"Custom name validation failed in {i+1} run"
