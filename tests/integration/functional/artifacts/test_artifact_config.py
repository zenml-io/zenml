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

from tests.integration.functional.utils import model_killer
from zenml import pipeline, step
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.client import Client
from zenml.constants import RUNNING_MODEL_VERSION
from zenml.enums import ModelStages
from zenml.model.model_config import ModelConfig
from zenml.models import (
    ModelRequestModel,
    ModelVersionArtifactFilterModel,
    ModelVersionRequestModel,
)

MODEL_NAME = "foo"


@step(model_config=ModelConfig(name=MODEL_NAME, create_new_model_version=True))
def single_output_step_from_context() -> Annotated[int, ArtifactConfig()]:
    """Untyped single output linked as Artifact from step context."""
    return 1


@step(model_config=ModelConfig(name=MODEL_NAME, create_new_model_version=True))
def single_output_step_from_context_model() -> (
    Annotated[int, ArtifactConfig(is_model_artifact=True)]
):
    """Untyped single output linked as Model Object from step context."""
    return 1


@step(model_config=ModelConfig(name=MODEL_NAME, create_new_model_version=True))
def single_output_step_from_context_deployment() -> (
    Annotated[int, ArtifactConfig(is_deployment_artifact=True)]
):
    """Untyped single output linked as Deployment from step context."""
    return 1


@pipeline(enable_cache=False)
def simple_pipeline():
    """Run 3 untyped single output linked from step context."""
    single_output_step_from_context()
    single_output_step_from_context_model(
        after=["single_output_step_from_context"]
    )
    single_output_step_from_context_deployment(
        after=["single_output_step_from_context_model"]
    )


def test_link_minimalistic():
    """Test simple explicit linking from step context for 3 artifact types."""
    with model_killer():
        client = Client()
        user = client.active_user.id
        ws = client.active_workspace.id

        simple_pipeline()

        model = client.get_model(MODEL_NAME)
        assert model.name == MODEL_NAME
        mv = client.get_model_version(MODEL_NAME)
        assert mv.name == "1"
        links = client.list_model_version_artifact_links(
            ModelVersionArtifactFilterModel(
                user_id=user,
                workspace_id=ws,
                model_id=model.id,
                model_version_id=mv.id,
            )
        )
        assert links.size == 3

        one_is_deployment = False
        one_is_model_object = False
        one_is_artifact = False
        for link in links:
            assert link.link_version == 1
            assert link.name == "output"
            one_is_deployment ^= (
                link.is_deployment and not link.is_model_object
            )
            one_is_model_object ^= (
                not link.is_deployment and link.is_model_object
            )
            one_is_artifact ^= (
                not link.is_deployment and not link.is_model_object
            )
        assert one_is_deployment
        assert one_is_model_object
        assert one_is_artifact


@step(model_config=ModelConfig(name=MODEL_NAME, create_new_model_version=True))
def multi_named_output_step_from_context() -> (
    Tuple[
        Annotated[int, "1", ArtifactConfig()],
        Annotated[int, "2", ArtifactConfig()],
        Annotated[int, "3", ArtifactConfig()],
    ]
):
    """3 typed output step with explicit linking from step context."""
    return 1, 2, 3


@pipeline(enable_cache=False)
def multi_named_pipeline():
    """3 typed output step with explicit linking from step context."""
    multi_named_output_step_from_context()


def test_link_multiple_named_outputs():
    """Test multiple typed output step with explicit linking from step context."""
    with model_killer():
        client = Client()
        user = client.active_user.id
        ws = client.active_workspace.id

        multi_named_pipeline()

        model = client.get_model(MODEL_NAME)
        assert model.name == MODEL_NAME
        mv = client.get_model_version(MODEL_NAME)
        assert mv.name == "1"
        al = client.list_model_version_artifact_links(
            ModelVersionArtifactFilterModel(
                user_id=user,
                workspace_id=ws,
                model_id=model.id,
                model_version_id=mv.id,
            )
        )
        assert al.size == 3
        assert (
            al[0].link_version + al[1].link_version + al[2].link_version == 3
        )
        assert {al.name for al in al} == {"1", "2", "3"}


@step(model_config=ModelConfig(name=MODEL_NAME, create_new_model_version=True))
def multi_named_output_step_not_tracked() -> (
    Tuple[
        Annotated[int, "1"],
        Annotated[int, "2"],
        Annotated[int, "3"],
    ]
):
    """Here links would be implicitly created based on step ModelConfig."""
    return 1, 2, 3


@pipeline(enable_cache=False)
def multi_named_pipeline_not_tracked():
    """Here links would be implicitly created based on step ModelConfig."""
    multi_named_output_step_not_tracked()


def test_link_multiple_named_outputs_without_links():
    """Test multi output step implicit linking based on step context."""
    with model_killer():
        client = Client()
        user = client.active_user.id
        ws = client.active_workspace.id

        multi_named_pipeline_not_tracked()

        model = client.get_model(MODEL_NAME)
        assert model.name == MODEL_NAME
        mv = client.get_model_version(MODEL_NAME)
        assert mv.name == "1"
        artifact_links = client.list_model_version_artifact_links(
            ModelVersionArtifactFilterModel(
                user_id=user,
                workspace_id=ws,
                model_id=model.id,
                model_version_id=mv.id,
            )
        )
        assert artifact_links.size == 3
        assert {al.name for al in artifact_links} == {"1", "2", "3"}


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


def test_link_multiple_named_outputs_with_self_context_and_caching():
    """Test multi output linking with context defined in Annotated."""
    with model_killer():
        client = Client()
        user = client.active_user.id
        ws = client.active_workspace.id

        # manual creation needed, as we work with specific versions
        m1 = ModelConfig(
            name=MODEL_NAME,
        ).get_or_create_model()
        m2 = ModelConfig(
            name="bar",
        ).get_or_create_model()

        mv1 = client.create_model_version(
            ModelVersionRequestModel(
                user=user,
                workspace=ws,
                name="bar",
                model=m1.id,
            )
        )
        mv2 = client.create_model_version(
            ModelVersionRequestModel(
                user=user,
                workspace=ws,
                name="foo",
                model=m2.id,
            )
        )

        for run_count in range(1, 3):
            multi_named_pipeline_from_self(run_count == 2)

            al1 = client.list_model_version_artifact_links(
                ModelVersionArtifactFilterModel(
                    user_id=user,
                    workspace_id=ws,
                    model_id=mv1.model.id,
                    model_version_id=mv1.id,
                )
            )
            al2 = client.list_model_version_artifact_links(
                ModelVersionArtifactFilterModel(
                    user_id=user,
                    workspace_id=ws,
                    model_id=mv2.model.id,
                    model_version_id=mv2.id,
                )
            )
            assert al1.size == 2
            assert al2.size == 1

            assert {al.name for al in al1} == {
                "1",
                "2",
            }
            assert al2[0].name == "3"

            # clean-up links to test caching linkage
            for mv, al in zip([mv1, mv2], [al1, al2]):
                for al_ in al:
                    client.zen_store.delete_model_version_artifact_link(
                        model_name_or_id=mv.model.id,
                        model_version_name_or_id=mv.id,
                        model_version_artifact_link_name_or_id=al_.id,
                    )


@step(model_config=ModelConfig(name="step", version="step"))
def multi_named_output_step_mixed_linkage() -> (
    Tuple[
        Annotated[
            int,
            "2",
            ArtifactConfig(),
        ],
        Annotated[
            int,
            "3",
            ArtifactConfig(model_name="artifact", model_version="artifact"),
        ],
    ]
):
    """Artifact "2"&"3" has own configs, but 2 will get step context and 3 defines own."""
    return 2, 3


@step
def pipeline_configuration_is_used_here() -> (
    Tuple[
        Annotated[int, "1", ArtifactConfig(name="custom_name")],
        Annotated[str, "4"],
    ]
):
    """Artifact "1" has own config and overrides name, but "4" will be implicitly tracked with pipeline config."""
    return 1, "foo"


@step
def some_plain_outputs():
    """This artifact will be implicitly tracked with pipeline config as a single tuple."""
    return "bar", 42.0


@step(model_config=ModelConfig(name="step", version="step"))
def and_some_typed_outputs() -> int:
    """This artifact can be implicitly tracked with step config."""
    return 1


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name="pipe", version="pipe"),
)
def multi_named_pipeline_mixed_linkage():
    """Mixed linking cases, see steps description."""
    pipeline_configuration_is_used_here()
    multi_named_output_step_mixed_linkage()
    some_plain_outputs()
    and_some_typed_outputs()


def test_link_multiple_named_outputs_with_mixed_linkage():
    """In this test a mixed linkage of artifacts is verified. See steps description."""
    with model_killer():
        client = Client()
        user = client.active_user.id
        ws = client.active_workspace.id

        # manual creation needed, as we work with specific versions
        models = []
        mvs = []
        for n in ["pipe", "step", "artifact"]:
            models.append(
                ModelConfig(
                    name=n,
                ).get_or_create_model()
            )
            mvs.append(
                client.create_model_version(
                    ModelVersionRequestModel(
                        user=user,
                        workspace=ws,
                        name=n,
                        model=models[-1].id,
                    )
                )
            )

        multi_named_pipeline_mixed_linkage()

        artifact_links = []
        for mv in mvs:
            artifact_links.append(
                client.list_model_version_artifact_links(
                    ModelVersionArtifactFilterModel(
                        user_id=user,
                        workspace_id=ws,
                        model_id=mv.model.id,
                        model_version_id=mv.id,
                    )
                )
            )

        assert artifact_links[0].size == 3
        assert artifact_links[1].size == 2
        assert artifact_links[2].size == 1

        assert {al.name for al in artifact_links[0]} == {
            "custom_name",
            "4",
            "output",
        }
        assert {al.name for al in artifact_links[1]} == {
            "2",
            "output",
        }
        assert artifact_links[2][0].name == "3"
        assert {al.link_version for al in artifact_links[0]} == {
            1
        }, "some artifacts tracked as higher versions, while all should be version 1"
        assert {al.link_version for al in artifact_links[1]} == {
            1
        }, "some artifacts tracked as higher versions, while all should be version 1"


@step(model_config=ModelConfig(name=MODEL_NAME, version="good_one"))
def single_output_step_no_versioning() -> (
    Annotated[int, ArtifactConfig(overwrite_model_link=True)]
):
    """Single output with overwrite and step context."""
    return 1


@pipeline(enable_cache=False)
def simple_pipeline_no_versioning():
    """Single output with overwrite and step context."""
    single_output_step_no_versioning()


def test_link_no_versioning():
    """Test that not versioned artifact is properly overwritten and no new versions created."""
    with model_killer():
        client = Client()
        user = client.active_user.id
        ws = client.active_workspace.id

        # manual creation needed, as we work with specific versions
        model = ModelConfig(
            name=MODEL_NAME,
        ).get_or_create_model()
        mv = client.create_model_version(
            ModelVersionRequestModel(
                user=user,
                workspace=ws,
                name="good_one",
                model=model.id,
            )
        )

        simple_pipeline_no_versioning()

        al1 = client.list_model_version_artifact_links(
            ModelVersionArtifactFilterModel(
                user_id=user,
                workspace_id=ws,
                model_id=model.id,
                model_version_id=mv.id,
            )
        )
        assert al1.size == 1
        assert al1[0].link_version == 1
        assert al1[0].name == "output"

        simple_pipeline_no_versioning()

        al2 = client.list_model_version_artifact_links(
            ModelVersionArtifactFilterModel(
                user_id=user,
                workspace_id=ws,
                model_id=model.id,
                model_version_id=mv.id,
            )
        )
        assert al2.size == 1
        assert al2[0].link_version == 1
        assert al2[0].name == "output"
        assert al1[0].id != al2[0].id


@step
def single_output_step_with_versioning() -> (
    Annotated[int, "predictions", ArtifactConfig(overwrite_model_link=False)]
):
    """Single output with overwrite disabled and step context."""
    return 1


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name=MODEL_NAME, stage=ModelStages.PRODUCTION),
)
def simple_pipeline_with_versioning():
    """Single output with overwrite disabled and step context."""
    single_output_step_with_versioning()


def test_link_with_versioning():
    """Test that versioned artifact is properly linked and new versions created."""
    with model_killer():
        client = Client()
        user = client.active_user.id
        ws = client.active_workspace.id

        # manual creation needed, as we work with specific versions
        model = client.create_model(
            ModelRequestModel(
                name=MODEL_NAME,
                user=user,
                workspace=ws,
            )
        )
        mv = client.create_model_version(
            ModelVersionRequestModel(
                user=user,
                workspace=ws,
                name="good_one",
                model=model.id,
            )
        )
        mv = mv.set_stage(ModelStages.PRODUCTION)

        simple_pipeline_with_versioning()

        al1 = client.list_model_version_artifact_links(
            ModelVersionArtifactFilterModel(
                user_id=user,
                workspace_id=ws,
                model_id=model.id,
                model_version_id=mv.id,
            )
        )
        assert al1.size == 1
        assert al1[0].link_version == 1
        assert al1[0].name == "predictions"

        simple_pipeline_with_versioning()

        al2 = client.list_model_version_artifact_links(
            ModelVersionArtifactFilterModel(
                user_id=user,
                workspace_id=ws,
                model_id=model.id,
                model_version_id=mv.id,
            )
        )
        assert al2.size == 2
        assert al2[0].link_version == 1
        assert al2[1].link_version == 2
        assert al2[0].name == al2[1].name
        assert al2[0].id != al2[1].id
        assert al1[0].id == al1[0].id


@step(enable_cache=True)
def _cacheable_step_annotated() -> (
    Annotated[str, "cacheable", ArtifactConfig()]
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
        ArtifactConfig(model_name="bar", model_version=RUNNING_MODEL_VERSION),
    ]
):
    return "cacheable"


@step(enable_cache=False)
def _non_cacheable_step():
    return "not cacheable"


def test_artifacts_linked_from_cache_steps():
    """Test that artifacts are linked from cache steps."""

    @pipeline(
        model_config=ModelConfig(name="foo", create_new_model_version=True),
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

    with model_killer():
        client = Client()

        for i in range(1, 3):
            fake_version = ModelConfig(
                name="bar", create_new_model_version=True
            ).get_or_create_model_version()
            _inner_pipeline(i != 1)

            mv = client.get_model_version(
                model_name_or_id="foo", model_version_name_or_number_or_id=i
            )
            assert len(mv.artifact_object_ids) == 2, f"Failed on {i} run"
            assert len(mv.model_object_ids) == 1, f"Failed on {i} run"
            assert set(mv.artifact_object_ids.keys()) == {
                "_inner_pipeline::_non_cacheable_step::output",
                "_inner_pipeline::_cacheable_step_not_annotated::output",
            }, f"Failed on {i} run"
            assert set(mv.model_object_ids.keys()) == {
                "_inner_pipeline::_cacheable_step_annotated::cacheable",
            }, f"Failed on {i} run"

            mv = client.get_model_version(
                model_name_or_id="bar",
                model_version_name_or_number_or_id=RUNNING_MODEL_VERSION,
            )
            assert len(mv.artifact_object_ids) == 1, f"Failed on {i} run"
            assert set(mv.artifact_object_ids.keys()) == {
                "_inner_pipeline::_cacheable_step_custom_model_annotated::cacheable",
            }, f"Failed on {i} run"
            assert (
                len(
                    mv.artifact_object_ids[
                        "_inner_pipeline::_cacheable_step_custom_model_annotated::cacheable"
                    ]
                )
                == 1
            ), f"Failed on {i} run"

            fake_version._update_default_running_version_name()


def test_artifacts_linked_from_cache_steps_same_id():
    """Test that artifacts are linked from cache steps with same id.
    This case appears if cached step is executed inside same model version
    and we need to silently pass linkage without failing on same id.
    """

    @pipeline(
        model_config=ModelConfig(name="foo", create_new_model_version=True),
        enable_cache=False,
    )
    def _inner_pipeline(force_disable_cache: bool = False):
        _cacheable_step_custom_model_annotated.with_options(
            enable_cache=force_disable_cache
        )()
        _non_cacheable_step()

    with model_killer():
        client = Client()

        for i in range(1, 3):
            ModelConfig(
                name="bar", create_new_model_version=True
            ).get_or_create_model_version()
            _inner_pipeline(i != 1)

            mv = client.get_model_version(
                model_name_or_id="bar",
                model_version_name_or_number_or_id=RUNNING_MODEL_VERSION,
            )
            assert len(mv.artifact_object_ids) == 1, f"Failed on {i} run"
            assert set(mv.artifact_object_ids.keys()) == {
                "_inner_pipeline::_cacheable_step_custom_model_annotated::cacheable",
            }, f"Failed on {i} run"
            assert (
                len(
                    mv.artifact_object_ids[
                        "_inner_pipeline::_cacheable_step_custom_model_annotated::cacheable"
                    ]
                )
                == 1
            ), f"Failed on {i} run"
