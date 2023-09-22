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
from contextlib import contextmanager
from typing import Callable, Tuple

import pytest
from typing_extensions import Annotated

from zenml import pipeline, step
from zenml.client import Client
from zenml.exceptions import EntityExistsError
from zenml.model import (
    ArtifactConfig,
    ModelConfig,
    ModelStages,
    link_output_to_model,
)
from zenml.models import (
    ModelRequestModel,
    ModelVersionArtifactFilterModel,
    ModelVersionRequestModel,
)

MODEL_NAME = "foo"


@contextmanager
def model_killer(model_name: str = MODEL_NAME):
    try:
        yield
    finally:
        zs = Client().zen_store
        zs.delete_model(model_name)


@step(model_config=ModelConfig(name=MODEL_NAME, create_new_model_version=True))
def single_output_step_from_context() -> Annotated[int, ArtifactConfig()]:
    return 1


@pipeline(enable_cache=False)
def simple_pipeline():
    single_output_step_from_context()


def test_link_minimalistic():
    with model_killer():
        zs = Client().zen_store
        user = Client().active_user.id
        ws = Client().active_workspace.id

        with pytest.raises(KeyError):
            zs.get_model(MODEL_NAME)

        simple_pipeline()

        model = zs.get_model(MODEL_NAME)
        assert model.name == MODEL_NAME
        mv = zs.get_model_version(MODEL_NAME)
        assert mv.version == "1"
        al = zs.list_model_version_artifact_links(
            ModelVersionArtifactFilterModel(
                user_id=user,
                workspace_id=ws,
                model_id=model.id,
                model_version_id=mv.id,
            )
        )
        assert al.size == 1
        assert al[0].link_version == 1
        assert al[0].name == "output"


@step(model_config=ModelConfig(name=MODEL_NAME, create_new_model_version=True))
def multi_named_output_step_from_context() -> (
    Tuple[
        Annotated[int, "1", ArtifactConfig()],
        Annotated[int, "2", ArtifactConfig()],
        Annotated[int, "3", ArtifactConfig()],
    ]
):
    return 1, 2, 3


@pipeline(enable_cache=False)
def multi_named_pipeline():
    multi_named_output_step_from_context()


def test_link_multiple_named_outputs():
    with model_killer():
        zs = Client().zen_store
        user = Client().active_user.id
        ws = Client().active_workspace.id

        with pytest.raises(KeyError):
            zs.get_model(MODEL_NAME)

        multi_named_pipeline()

        model = zs.get_model(MODEL_NAME)
        assert model.name == MODEL_NAME
        mv = zs.get_model_version(MODEL_NAME)
        assert mv.version == "1"
        al = zs.list_model_version_artifact_links(
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
        assert al[0].name == "1"
        assert al[1].name == "2"
        assert al[2].name == "3"


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
    multi_named_output_step_not_tracked()


def test_link_multiple_named_outputs_without_links():
    with model_killer():
        zs = Client().zen_store
        user = Client().active_user.id
        ws = Client().active_workspace.id

        multi_named_pipeline_not_tracked()

        model = zs.get_model(MODEL_NAME)
        assert model.name == MODEL_NAME
        mv = zs.get_model_version(MODEL_NAME)
        assert mv.version == "1"
        artifact_links = zs.list_model_version_artifact_links(
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
            ArtifactConfig(model_name=MODEL_NAME, model_version_name="bar"),
        ],
        Annotated[
            int,
            "2",
            ArtifactConfig(model_name=MODEL_NAME, model_version_name="bar"),
        ],
        Annotated[
            int,
            "3",
            ArtifactConfig(model_name="bar", model_version_name="foo"),
        ],
    ]
):
    return 1, 2, 3


@pipeline(enable_cache=False)
def multi_named_pipeline_from_self():
    multi_named_output_step_from_self()


def test_link_multiple_named_outputs_with_self_context():
    with model_killer():
        with model_killer("bar"):
            zs = Client().zen_store
            user = Client().active_user.id
            ws = Client().active_workspace.id

            # manual creation needed, as we work with specific versions
            m1 = ModelConfig(
                name=MODEL_NAME,
            ).get_or_create_model()
            m2 = ModelConfig(
                name="bar",
            ).get_or_create_model()

            mv1 = zs.create_model_version(
                ModelVersionRequestModel(
                    user=user,
                    workspace=ws,
                    version="bar",
                    model=m1.id,
                )
            )
            mv2 = zs.create_model_version(
                ModelVersionRequestModel(
                    user=user,
                    workspace=ws,
                    version="foo",
                    model=m2.id,
                )
            )

            multi_named_pipeline_from_self()

            al1 = zs.list_model_version_artifact_links(
                ModelVersionArtifactFilterModel(
                    user_id=user,
                    workspace_id=ws,
                    model_id=mv1.model.id,
                    model_version_id=mv1.id,
                )
            )
            al2 = zs.list_model_version_artifact_links(
                ModelVersionArtifactFilterModel(
                    user_id=user,
                    workspace_id=ws,
                    model_id=mv2.model.id,
                    model_version_id=mv2.id,
                )
            )
            assert al1.size == 2
            assert al2.size == 1

            assert al1[0].name == "1"
            assert al1[1].name == "2"
            assert al2[0].name == "3"


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
            ArtifactConfig(
                model_name="artifact", model_version_name="artifact"
            ),
        ],
    ]
):
    """Artifact "2"&"3" has own configs."""
    return 2, 3


@step
def pipeline_configuration_is_used_here() -> (
    Tuple[
        Annotated[int, "1", ArtifactConfig(artifact_name="custom_name")],
        Annotated[str, "4"],
    ]
):
    """Artifact "1" has own config, but "4" can be implicitly tracked with pipeline config."""
    return 1, "foo"


@step
def some_plain_outputs():
    """This artifact can be implicitly tracked with pipeline config as a single tuple."""
    return "bar", 42.0


@step
def and_some_typed_outputs() -> int:
    """This artifact can be implicitly tracked with pipeline config."""
    return 1


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name="pipe", version="pipe"),
)
def multi_named_pipeline_mixed_linkage():
    pipeline_configuration_is_used_here()
    multi_named_output_step_mixed_linkage()
    some_plain_outputs()
    and_some_typed_outputs()


def test_link_multiple_named_outputs_with_mixed_linkage():
    """In this test a mixed linkage of artifacts is verified."""
    with model_killer("pipe"):
        with model_killer("step"):
            with model_killer("artifact"):
                zs = Client().zen_store
                user = Client().active_user.id
                ws = Client().active_workspace.id

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
                        zs.create_model_version(
                            ModelVersionRequestModel(
                                user=user,
                                workspace=ws,
                                version=n,
                                model=models[-1].id,
                            )
                        )
                    )

                multi_named_pipeline_mixed_linkage()

                artifact_links = []
                for mv in mvs:
                    artifact_links.append(
                        zs.list_model_version_artifact_links(
                            ModelVersionArtifactFilterModel(
                                user_id=user,
                                workspace_id=ws,
                                model_id=mv.model.id,
                                model_version_id=mv.id,
                            )
                        )
                    )

                assert artifact_links[0].size == 4
                assert artifact_links[1].size == 1
                assert artifact_links[2].size == 1

                assert {al.name for al in artifact_links[0]} == {
                    "custom_name",
                    "4",
                    "output",
                }
                assert {al.version for al in artifact_links[0]} == {
                    1
                }, "some artifacts tracked as higher versions, while all should be version 1"
                assert artifact_links[1][0].name == "2"
                assert artifact_links[2][0].name == "3"


@step(model_config=ModelConfig(name=MODEL_NAME, version="good_one"))
def single_output_step_no_versioning() -> (
    Annotated[int, ArtifactConfig(overwrite=True)]
):
    return 1


@pipeline(enable_cache=False)
def simple_pipeline_no_versioning():
    single_output_step_no_versioning()


def test_link_no_versioning():
    with model_killer():
        zs = Client().zen_store
        user = Client().active_user.id
        ws = Client().active_workspace.id

        # manual creation needed, as we work with specific versions
        model = ModelConfig(
            name=MODEL_NAME,
        ).get_or_create_model()
        mv = zs.create_model_version(
            ModelVersionRequestModel(
                user=user,
                workspace=ws,
                version="good_one",
                model=model.id,
            )
        )

        simple_pipeline_no_versioning()

        al1 = zs.list_model_version_artifact_links(
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

        al2 = zs.list_model_version_artifact_links(
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
    return 1


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name=MODEL_NAME, stage=ModelStages.PRODUCTION),
)
def simple_pipeline_with_versioning():
    single_output_step_with_versioning()


def test_link_with_versioning():
    with model_killer():
        zs = Client().zen_store
        user = Client().active_user.id
        ws = Client().active_workspace.id

        # manual creation needed, as we work with specific versions
        model = zs.create_model(
            ModelRequestModel(
                name=MODEL_NAME,
                user=user,
                workspace=ws,
            )
        )
        mv = zs.create_model_version(
            ModelVersionRequestModel(
                user=user,
                workspace=ws,
                version="good_one",
                model=model.id,
            )
        )
        mv = mv.set_stage(ModelStages.PRODUCTION)

        simple_pipeline_with_versioning()

        al1 = zs.list_model_version_artifact_links(
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

        al2 = zs.list_model_version_artifact_links(
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
    link_output_to_model(ArtifactConfig(), "1")
    link_output_to_model(
        ArtifactConfig(model_name="bar", model_version_name="bar"), "2"
    )
    return 1, 2


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name=MODEL_NAME),
)
def simple_pipeline_with_manual_linkage():
    step_with_manual_linkage()


@step
def step_with_manual_and_implicit_linkage() -> (
    Tuple[Annotated[int, "1"], Annotated[int, "2"]]
):
    link_output_to_model(
        ArtifactConfig(model_name="bar", model_version_name="bar"), "2"
    )
    return 1, 2


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name=MODEL_NAME),
)
def simple_pipeline_with_manual_and_implicit_linkage():
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
    with model_killer():
        with model_killer("bar"):
            zs = Client().zen_store
            user = Client().active_user.id
            ws = Client().active_workspace.id

            # manual creation needed, as we work with specific versions
            model = zs.create_model(
                ModelRequestModel(
                    name=MODEL_NAME,
                    user=user,
                    workspace=ws,
                )
            )
            model2 = zs.create_model(
                ModelRequestModel(
                    name="bar",
                    user=user,
                    workspace=ws,
                )
            )
            mv = zs.create_model_version(
                ModelVersionRequestModel(
                    user=user,
                    workspace=ws,
                    version="good_one",
                    model=model.id,
                )
            )
            mv2 = zs.create_model_version(
                ModelVersionRequestModel(
                    user=user,
                    workspace=ws,
                    version="bar",
                    model=model2.id,
                )
            )

            pipeline()

            al1 = zs.list_model_version_artifact_links(
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

            al2 = zs.list_model_version_artifact_links(
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
    with pytest.raises(EntityExistsError):
        link_output_to_model(ArtifactConfig(), "1")
    return 1


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name=MODEL_NAME),
)
def simple_pipeline_with_manual_linkage_fail_on_override():
    step_with_manual_linkage_fail_on_override()


def test_link_with_manual_linkage_fail_on_override():
    with model_killer():
        zs = Client().zen_store
        user = Client().active_user.id
        ws = Client().active_workspace.id

        # manual creation needed, as we work with specific versions
        model = zs.create_model(
            ModelRequestModel(
                name=MODEL_NAME,
                user=user,
                workspace=ws,
            )
        )
        zs.create_model_version(
            ModelVersionRequestModel(
                user=user,
                workspace=ws,
                version="good_one",
                model=model.id,
            )
        )

        simple_pipeline_with_manual_linkage_fail_on_override()
