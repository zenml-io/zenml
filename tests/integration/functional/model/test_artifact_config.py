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
from typing import Callable, Tuple

import pytest
from typing_extensions import Annotated

from tests.integration.functional.utils import model_killer
from zenml import pipeline, step
from zenml.client import Client
from zenml.enums import ModelStages
from zenml.exceptions import EntityExistsError
from zenml.model import (
    ArtifactConfig,
    DeploymentArtifactConfig,
    ModelArtifactConfig,
    ModelConfig,
    link_output_to_model,
)
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
    Annotated[int, ModelArtifactConfig(save_to_model_registry=True)]
):
    """Untyped single output linked as Model Object from step context."""
    return 1


@step(model_config=ModelConfig(name=MODEL_NAME, create_new_model_version=True))
def single_output_step_from_context_deployment() -> (
    Annotated[int, DeploymentArtifactConfig()]
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


@pipeline(enable_cache=False)
def multi_named_pipeline_from_self():
    """Multi output linking from Annotated."""
    multi_named_output_step_from_self()


def test_link_multiple_named_outputs_with_self_context():
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

        multi_named_pipeline_from_self()

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


@step(model_config=ModelConfig(name="step", version_name="step"))
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
        Annotated[int, "1", ArtifactConfig(artifact_name="custom_name")],
        Annotated[str, "4"],
    ]
):
    """Artifact "1" has own config and overrides name, but "4" will be implicitly tracked with pipeline config."""
    return 1, "foo"


@step
def some_plain_outputs():
    """This artifact will be implicitly tracked with pipeline config as a single tuple."""
    return "bar", 42.0


@step(model_config=ModelConfig(name="step", version_name="step"))
def and_some_typed_outputs() -> int:
    """This artifact can be implicitly tracked with step config."""
    return 1


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name="pipe", version_name="pipe"),
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


@step(model_config=ModelConfig(name=MODEL_NAME, version_name="good_one"))
def single_output_step_no_versioning() -> (
    Annotated[int, ArtifactConfig(overwrite=True)]
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
    Annotated[int, "predictions", ArtifactConfig(overwrite=False)]
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


@step
def step_with_manual_linkage() -> (
    Tuple[Annotated[int, "1"], Annotated[int, "2"]]
):
    """Multi output linking by function."""
    link_output_to_model(ArtifactConfig(), "1")
    link_output_to_model(
        ArtifactConfig(model_name="bar", model_version="bar"), "2"
    )
    return 1, 2


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name=MODEL_NAME),
)
def simple_pipeline_with_manual_linkage():
    """Multi output linking by function."""
    step_with_manual_linkage()


@step
def step_with_manual_and_implicit_linkage() -> (
    Tuple[Annotated[int, "1"], Annotated[int, "2"]]
):
    """Multi output: 2 is linked by function, 1 is linked implicitly."""
    link_output_to_model(
        ArtifactConfig(model_name="bar", model_version="bar"), "2"
    )
    return 1, 2


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name=MODEL_NAME),
)
def simple_pipeline_with_manual_and_implicit_linkage():
    """Multi output: 2 is linked by function, 1 is linked implicitly."""
    step_with_manual_and_implicit_linkage()


@pytest.mark.parametrize(
    "pipeline",
    (
        simple_pipeline_with_manual_linkage,
        simple_pipeline_with_manual_and_implicit_linkage,
    ),
    ids=("manual_linkage_only", "manual_and_implicit"),
)
def test_link_with_manual_linkage(pipeline: Callable):
    """Test manual linking by function call in 2 setting: only manual and manual+implicit"""
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
        model2 = client.create_model(
            ModelRequestModel(
                name="bar",
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
        mv2 = client.create_model_version(
            ModelVersionRequestModel(
                user=user,
                workspace=ws,
                name="bar",
                model=model2.id,
            )
        )

        pipeline()

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
        assert al1[0].name == "1"

        al2 = client.list_model_version_artifact_links(
            ModelVersionArtifactFilterModel(
                user_id=user,
                workspace_id=ws,
                model_id=model2.id,
                model_version_id=mv2.id,
            )
        )
        assert al2.size == 1
        assert al2[0].link_version == 1
        assert al2[0].name == "2"


@step
def step_with_manual_linkage_fail_on_override() -> (
    Annotated[int, "1", ArtifactConfig()]
):
    """Should fail on manual linkage, cause Annotated provided."""
    with pytest.raises(EntityExistsError):
        link_output_to_model(ArtifactConfig(), "1")
    return 1


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name=MODEL_NAME),
)
def simple_pipeline_with_manual_linkage_fail_on_override():
    """Should fail on manual linkage, cause Annotated provided."""
    step_with_manual_linkage_fail_on_override()


def test_link_with_manual_linkage_fail_on_override():
    """Test that step fails on manual linkage, cause Annotated provided."""
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
        client.create_model_version(
            ModelVersionRequestModel(
                user=user,
                workspace=ws,
                name="good_one",
                model=model.id,
            )
        )

        simple_pipeline_with_manual_linkage_fail_on_override()


@step
def step_with_manual_linkage_flexible_config(
    artifact_config: ArtifactConfig,
) -> Annotated[int, "1"]:
    """Flexible manual linkage based on input arg."""
    link_output_to_model(artifact_config, "1")
    return 1


@pipeline(enable_cache=False)
def simple_pipeline_with_manual_linkage_flexible_config(
    artifact_config: ArtifactConfig,
):
    """Flexible manual linkage based on input arg."""
    step_with_manual_linkage_flexible_config(artifact_config)


@pytest.mark.parametrize(
    "artifact_config",
    (
        ArtifactConfig(model_name=MODEL_NAME, model_version="good_one"),
        ArtifactConfig(
            model_name=MODEL_NAME, model_version=ModelStages.PRODUCTION
        ),
        ArtifactConfig(model_name=MODEL_NAME),
        ArtifactConfig(model_name=MODEL_NAME, model_version=1),
    ),
    ids=("exact_version", "exact_stage", "latest_version", "exact_number"),
)
def test_link_with_manual_linkage_flexible_config(
    artifact_config: ArtifactConfig,
):
    """Test that linking using ArtifactConfig is possible for exact version, stage and latest versions."""
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
        mv.set_stage(ModelStages.PRODUCTION)

        simple_pipeline_with_manual_linkage_flexible_config(artifact_config)

        links = client.list_model_version_artifact_links(
            ModelVersionArtifactFilterModel(
                user_id=user,
                workspace_id=ws,
                model_id=model.id,
                model_version_id=mv.id,
            )
        )
        assert len(links) == 1
        assert links[0].link_version == 1
        assert links[0].name == "1"
