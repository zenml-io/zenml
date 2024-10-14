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
from typing import Optional
from unittest import mock
from unittest.mock import patch

import pytest
from typing_extensions import Annotated

from tests.integration.functional.utils import random_str
from zenml import get_step_context, pipeline, step
from zenml.artifacts.utils import save_artifact
from zenml.client import Client
from zenml.enums import ModelStages
from zenml.model.model import Model
from zenml.model.utils import link_artifact_to_model, log_model_metadata
from zenml.models import TagRequest


class ModelContext:
    def __init__(
        self,
        create_model: bool = True,
        version: str = None,
        stage: str = None,
    ):
        client = Client()
        self.workspace = client.active_workspace.id
        self.user = client.active_user.id
        self.create_model = create_model
        self.version = version
        self.stage = stage
        self.model_name = f"mdl_{random_str(20)}"

    def __enter__(self):
        if self.create_model:
            client = Client()
            model = client.create_model(
                name=self.model_name,
            )
            if self.version is not None:
                mv = client.create_model_version(
                    model_name_or_id=model.id,
                    name=self.version,
                )
                if self.stage is not None:
                    mv.set_stage(self.stage)
                return self.model_name, model, mv
            return self.model_name, model, None
        return self.model_name, None, None

    def __exit__(self, exc_type, exc_value, exc_traceback):
        client = Client()
        try:
            client.delete_model(model_name_or_id=self.model_name)
        except KeyError:
            pass


class TagContext:
    def __init__(
        self,
        do_create: bool = True,
        name: str = None,
        color: str = None,
    ):
        self.do_create = do_create
        if name is not None:
            self.name = name
        else:
            self.name = f"tag_{random_str(20)}"
        self.color = color

    def __enter__(self):
        if self.do_create:
            client = Client()
            try:
                if self.color is not None:
                    client.create_tag(
                        TagRequest(name=self.name, color=self.color)
                    )
                else:
                    client.create_tag(TagRequest(name=self.name))
            except KeyError:
                pass
        return self.name

    def __exit__(self, exc_type, exc_value, exc_traceback):
        client = Client()
        try:
            client.delete_tag(self.name)
        except KeyError:
            pass


@step
def step_metadata_logging_functional(mdl_name: str):
    """Functional logging using implicit Model from context."""
    log_model_metadata({"foo": "bar"})
    assert get_step_context().model.run_metadata["foo"].value == "bar"
    log_model_metadata(
        {"foo": "bar"}, model_name=mdl_name, model_version="other"
    )


@step
def simple_producer() -> str:
    """Simple producer step."""
    return "foo"


@step
def artifact_linker(
    artifact_name: str,
    model: Optional[Model] = None,
    is_model_artifact: bool = False,
    is_deployment_artifact: bool = False,
) -> None:
    """Step linking an artifact to a model via function or implicit."""

    artifact = save_artifact(
        data="Hello, World!",
        name=artifact_name,
        is_model_artifact=is_model_artifact,
        is_deployment_artifact=is_deployment_artifact,
    )

    if model:
        link_artifact_to_model(
            artifact_version=artifact,
            model=model,
            is_model_artifact=is_model_artifact,
            is_deployment_artifact=is_deployment_artifact,
        )


@step
def consume_from_model(
    is_consume: bool,
) -> Annotated[str, "custom_output"]:
    """A step which can either produce string output or read and return it from model version 1."""
    if is_consume:
        mv_context = get_step_context().model
        mv = Model(name=mv_context.name, version="1")
        return mv.load_artifact("custom_output")
    else:
        return "Hello, World!"


def parallel_model_version_creation(model_name: str) -> int:
    with patch("zenml.model.model.logger.debug") as logger_mock:
        Model(name=model_name)._get_or_create_model_version()
        return logger_mock.call_count


class TestModel:
    def test_model_created_with_warning(self):
        """Test if the model is created with a warning.

        It then checks if an info is logged during the creation process.
        Info is expected because the model is not yet created.
        """
        with ModelContext(create_model=False) as (mdl_name, _, _):
            mv = Model(name=mdl_name)
            with mock.patch("zenml.model.model.logger.info") as logger:
                model = mv._get_or_create_model()
                logger.assert_called_once()
            assert model.name == mdl_name

    def test_model_exists(self):
        """Test if model fetched fine, if exists."""
        with ModelContext() as (mdl_name, model, _):
            mv = Model(name=mdl_name)
            with mock.patch("zenml.model.model.logger.warning") as logger:
                model2 = mv._get_or_create_model()
                logger.assert_not_called()
            assert model.name == model2.name
            assert model.id == model2.id

    def test_model_create_model_and_version(self):
        """Test if model and version are created, not existing before."""
        with ModelContext(create_model=False) as (mdl_name, _, _):
            mv = Model(name=mdl_name, tags=["tag1", "tag2"])
            with mock.patch("zenml.model.model.logger.info") as logger:
                mv = mv._get_or_create_model_version()
                logger.assert_called()
            assert mv.name == str(mv.number)
            assert mv.model.name == mdl_name
            assert {t.name for t in mv.tags} == {"tag1", "tag2"}
            assert {t.name for t in mv.model.tags} == {"tag1", "tag2"}

    def test_create_model_version_makes_proper_tagging(self):
        """Test if model versions get unique tags."""
        with ModelContext(create_model=False) as (mdl_name, _, _):
            mv = Model(name=mdl_name, tags=["tag1", "tag2"])
            mv = mv._get_or_create_model_version()
            assert mv.name == str(mv.number)
            assert mv.model.name == mdl_name
            assert {t.name for t in mv.tags} == {"tag1", "tag2"}
            assert {t.name for t in mv.model.tags} == {"tag1", "tag2"}

            mv = Model(name=mdl_name, tags=["tag3", "tag4"])
            mv = mv._get_or_create_model_version()
            assert mv.name == str(mv.number)
            assert mv.model.name == mdl_name
            assert {t.name for t in mv.tags} == {"tag3", "tag4"}
            assert {t.name for t in mv.model.tags} == {"tag1", "tag2"}

    def test_model_fetch_model_and_version_by_number(self):
        """Test model and model version retrieval by exact version number."""
        with ModelContext(version="1.0.0") as (mdl_name, model, mv):
            mv = Model(name=mdl_name, version="1.0.0")
            with mock.patch("zenml.model.model.logger.warning") as logger:
                mv_test = mv._get_or_create_model_version()
                logger.assert_not_called()
            assert mv_test.id == mv.id
            assert mv_test.model.name == model.name

    def test_model_fetch_model_and_version_by_number_not_found(self):
        """Test model and model version retrieval fails by exact version number, if version missing."""
        with ModelContext() as (mdl_name, _, _):
            mv = Model(name=mdl_name, version="1.0.0")
            with pytest.raises(KeyError):
                mv._get_model_version()

    def test_model_fetch_model_and_version_by_stage(self):
        """Test model and model version retrieval by exact stage number."""
        with ModelContext(version="1.0.0", stage=ModelStages.PRODUCTION) as (
            mdl_name,
            model,
            mv,
        ):
            mv = Model(name=mdl_name, version=ModelStages.PRODUCTION)
            with mock.patch("zenml.model.model.logger.warning") as logger:
                mv_test = mv._get_or_create_model_version()
                logger.assert_not_called()
            assert mv_test.id == mv.id
            assert mv_test.model.name == model.name

    def test_model_fetch_model_and_version_by_stage_not_found(self):
        """Test model and model version retrieval fails by exact stage number, if version in stage missing."""
        with ModelContext(version="1.0.0") as (mdl_name, _, _):
            mv = Model(name=mdl_name, version=ModelStages.PRODUCTION)
            with pytest.raises(KeyError):
                mv._get_model_version()

    def test_model_fetch_model_and_version_latest(self):
        """Test model and model version retrieval by latest version."""
        with ModelContext(version="1.0.0") as (mdl_name, _, _):
            mv = Model(name=mdl_name, version=ModelStages.LATEST)
            mv = mv._get_or_create_model_version()

            assert mv.name == "1.0.0"

    def test_init_stage_logic(self):
        """Test that if version is set to string contained in ModelStages user is informed about it."""
        with ModelContext(create_model=False) as (mdl_name, _, _):
            with mock.patch("zenml.model.model.logger.info") as logger:
                mv = Model(
                    name=mdl_name,
                    version=ModelStages.PRODUCTION.value,
                )
                logger.assert_called_once()
                assert mv.version == ModelStages.PRODUCTION.value

            mv = Model(name=mdl_name, version=ModelStages.PRODUCTION)
            assert mv.version == ModelStages.PRODUCTION

    def test_recovery_flow(self):
        """Test that model context can recover same version after failure."""
        with ModelContext() as (mdl_name, _, _):
            mv = Model(name=mdl_name)
            mv1 = mv._get_or_create_model_version()
            del mv

            mv = Model(name=mdl_name, version=1)
            mv2 = mv._get_or_create_model_version()

            assert mv1.id == mv2.id

    def test_tags_properly_created(self):
        """Test that model context can create proper tag relationships."""
        with ModelContext(create_model=False) as (mdl_name, _, _):
            with TagContext(color="green") as green_tag:
                with TagContext(do_create=False) as new_tag:
                    mv = Model(
                        name=mdl_name,
                        tags=[green_tag, new_tag],
                    )

                    # run 2 times to first create, next get
                    for _ in range(2):
                        model = mv._get_or_create_model()

                        assert len(model.tags) == 2
                        assert {t.name for t in model.tags} == {
                            green_tag,
                            new_tag,
                        }
                        assert {
                            t.color for t in model.tags if t.name == green_tag
                        } == {"green"}

    def test_tags_properly_updated(self):
        """Test that model context can update proper tag relationships."""
        with ModelContext(create_model=False) as (mdl_name, _, _):
            client = Client()
            mv = Model(
                name=mdl_name,
                tags=["foo", "bar"],
            )
            model_id = mv._get_or_create_model_version().model.id

            client.update_model(model_id, add_tags=["tag1", "tag2"])
            model = mv._get_or_create_model()
            assert len(model.tags) == 4
            assert {t.name for t in model.tags} == {
                "foo",
                "bar",
                "tag1",
                "tag2",
            }

            client.update_model_version(
                model_id, "1", add_tags=["tag3", "tag4"]
            )
            model_version = mv._get_or_create_model_version()
            assert len(model_version.tags) == 4
            assert {t.name for t in model_version.tags} == {
                "foo",
                "bar",
                "tag3",
                "tag4",
            }

            client.update_model(model_id, remove_tags=["tag1", "tag2"])
            model = mv._get_or_create_model()
            assert len(model.tags) == 2
            assert {t.name for t in model.tags} == {"foo", "bar"}

            client.update_model_version(
                model_id, "1", remove_tags=["tag3", "tag4"]
            )
            model_version = mv._get_or_create_model_version()
            assert len(model_version.tags) == 2
            assert {t.name for t in model_version.tags} == {"foo", "bar"}

    def test_model_version_config_differs_from_db_warns(self):
        """Test that model version context warns if model version config differs from db."""
        with ModelContext(create_model=False) as (mdl_name, _, _):
            mv = Model(
                name=mdl_name,
                version="1.0.0",
                tags=["foo", "bar"],
            )
            mv._get_or_create_model_version()

            mv = Model(
                name=mdl_name,
                version="1.0.0",
                tags=["bar", "new"],
                license="NEW",
                description="NEW",
                save_models_to_registry=False,
            )
            with mock.patch("zenml.model.model.logger.warning") as logger:
                mv._get_or_create_model_version()
                logger.assert_called_once()

                warning = logger.call_args[0][0]
                assert "tags added" in warning
                assert "tags removed" in warning
                assert "description" in warning

    def test_metadata_logging(self):
        """Test that model version can be used to track metadata from object."""
        with ModelContext() as (mdl_name, _, _):
            mv = Model(
                name=mdl_name,
                description="foo",
            )
            mv.log_metadata({"foo": "bar"})

            assert len(mv.run_metadata) == 1
            assert mv.run_metadata["foo"].value == "bar"

            mv.log_metadata({"bar": "foo"})

            assert len(mv.run_metadata) == 2
            assert mv.run_metadata["foo"].value == "bar"
            assert mv.run_metadata["bar"].value == "foo"

    def test_metadata_logging_functional(self):
        """Test that model version can be used to track metadata from function."""
        with ModelContext(create_model=False) as (mdl_name, _, _):
            mv = Model(
                name=mdl_name,
                description="foo",
            )
            mv._get_or_create_model_version()

            log_model_metadata(
                {"foo": "bar"}, model_name=mv.name, model_version=mv.number
            )

            assert len(mv.run_metadata) == 1
            assert mv.run_metadata["foo"].value == "bar"

            with pytest.raises(ValueError):
                log_model_metadata({"foo": "bar"})

            log_model_metadata(
                {"bar": "foo"}, model_name=mv.name, model_version="latest"
            )

            assert len(mv.run_metadata) == 2
            assert mv.run_metadata["foo"].value == "bar"
            assert mv.run_metadata["bar"].value == "foo"

    def test_metadata_logging_in_steps(self):
        """Test that model version can be used to track metadata from function in steps."""
        with ModelContext(create_model=False) as (mdl_name, _, _):

            @pipeline(
                model=Model(name=mdl_name, version="context"),
                enable_cache=False,
            )
            def my_pipeline():
                step_metadata_logging_functional(mdl_name)

            mv_other = Model(
                name=mdl_name,
                version="other",
            )
            mv_other._get_or_create_model_version()

            my_pipeline()

            mv = Model(name=mdl_name, version="context")
            assert len(mv.run_metadata) == 1
            assert mv.run_metadata["foo"].value == "bar"

            mv = Model(name=mdl_name, version="other")
            assert len(mv.run_metadata) == 1
            assert mv.run_metadata["foo"].value == "bar"

    @pytest.mark.parametrize("delete_artifacts", [False, True])
    def test_deletion_of_links(self, delete_artifacts: bool):
        """Test that user can delete artifact links (with artifacts) from Model."""
        with ModelContext(create_model=False) as (mdl_name, _, _):

            @pipeline(
                model=Model(
                    name=mdl_name,
                ),
                enable_cache=False,
            )
            def _inner_pipeline_test_deletion_of_links():
                simple_producer()
                simple_producer(id="other_named_producer")

            _inner_pipeline_test_deletion_of_links()

            client = Client()
            mv = Model(name=mdl_name, version="latest")
            artifact_ids = mv._get_model_version().data_artifact_ids
            assert len(artifact_ids) == 2

            # delete run to enable artifacts deletion
            run = client.list_pipeline_runs(
                pipeline="_inner_pipeline_test_deletion_of_links",
                sort_by="desc:start_time",
            ).items[0]
            client.delete_pipeline_run(run.id)

            mv.delete_artifact(
                only_link=not delete_artifacts,
                name="_inner_pipeline_test_deletion_of_links::other_named_producer::output",
            )
            assert len(mv._get_model_version().data_artifact_ids) == 1
            versions_ = artifact_ids[
                "_inner_pipeline_test_deletion_of_links::other_named_producer::output"
            ]
            first_version_ = versions_[min(versions_.keys())]
            if delete_artifacts:
                with pytest.raises(KeyError):
                    client.get_artifact_version(first_version_)
            else:
                assert (
                    client.get_artifact_version(first_version_).id
                    == first_version_
                )

            _inner_pipeline_test_deletion_of_links()
            mv = Model(name=mdl_name, version="latest")
            artifact_ids = mv._get_model_version().data_artifact_ids
            assert len(artifact_ids) == 2

            # delete run to enable artifacts deletion
            run = client.list_pipeline_runs(
                pipeline="_inner_pipeline_test_deletion_of_links",
                sort_by="desc:start_time",
            ).items[0]
            client.delete_pipeline_run(run.id)

            mv.delete_all_artifacts(only_link=not delete_artifacts)
            assert len(mv._get_model_version().data_artifact_ids) == 0
            for versions_ in artifact_ids.values():
                for id_ in versions_.values():
                    if delete_artifacts:
                        with pytest.raises(KeyError):
                            client.get_artifact_version(id_)
                    else:
                        assert client.get_artifact_version(id_).id == id_

    def test_that_artifacts_are_not_linked_to_models_outside_of_the_context(
        self,
    ):
        """Test that artifacts are linked only to model versions from the context."""

        with ModelContext(create_model=False) as (mdl_name, _, _):

            @pipeline(model=Model(name=mdl_name))
            def my_pipeline(is_consume: bool):
                consume_from_model(is_consume)

            my_pipeline(False)
            mv = Model(name=mdl_name, version="latest")
            assert mv.number == 1
            assert len(mv._get_model_version().data_artifact_ids) == 1

            my_pipeline(True)
            mv = Model(name=mdl_name, version="latest")
            assert mv.number == 2
            assert len(mv._get_model_version().data_artifact_ids) == 1
            mv = Model(name=mdl_name, version="1")
            assert len(mv._get_model_version().data_artifact_ids) == 1

    def test_link_artifact_via_function(self):
        """Test that user can link artifacts via function to a model version."""
        artifact_name = f"art_{random_str(20)}"
        try:
            with ModelContext(create_model=False) as (mdl_name, _, _):
                with ModelContext(create_model=False) as (
                    custom_mdl_name,
                    _,
                    _,
                ):

                    @pipeline
                    def _inner_pipeline(
                        model: Model = None,
                        is_model_artifact: bool = False,
                        is_deployment_artifact: bool = False,
                    ):
                        artifact_linker(
                            artifact_name=artifact_name,
                            model=model,
                            is_model_artifact=is_model_artifact,
                            is_deployment_artifact=is_deployment_artifact,
                        )

                    mv_in_pipe = Model(
                        name=mdl_name,
                    )

                    # no context, no model, artifact produced but not linked
                    _inner_pipeline()
                    artifact = Client().get_artifact_version(artifact_name)
                    assert int(artifact.version) == 1

                    # pipeline will run in a model context and will use cached step version
                    _inner_pipeline.with_options(model=mv_in_pipe)()

                    mv = Model(name=mdl_name, version="latest")
                    assert mv.number == 1
                    artifact = mv.get_artifact(artifact_name)
                    assert artifact.load() == "Hello, World!"
                    assert int(artifact.version) == 1

                    # use custom model version (cache invalidated)
                    _inner_pipeline(model=Model(name=custom_mdl_name))

                    mv_custom = Model(name=custom_mdl_name, version="latest")
                    assert mv_custom.number == 1
                    artifact = mv_custom.get_artifact(artifact_name)
                    assert artifact.load() == "Hello, World!"
                    assert int(artifact.version) == 2

                    # use context + model (cache invalidated)
                    _inner_pipeline.with_options(model=mv_in_pipe)(
                        is_model_artifact=True
                    )

                    mv = Model(name=mdl_name, version="latest")
                    assert mv.number == 2
                    artifact = mv.get_artifact(artifact_name)
                    assert artifact.load() == "Hello, World!"
                    assert int(artifact.version) == 3

                    # use context + deployment (cache invalidated)
                    _inner_pipeline.with_options(model=mv_in_pipe)(
                        is_deployment_artifact=True
                    )

                    mv = Model(name=mdl_name, version="latest")
                    assert mv.number == 3
                    artifact = mv.get_deployment_artifact(artifact_name)
                    assert artifact.load() == "Hello, World!"
                    assert int(artifact.version) == 4

                    # link outside of a step
                    artifact = save_artifact(
                        data="Hello, World!", name=artifact_name
                    )
                    link_artifact_to_model(
                        artifact_version=artifact,
                        model=Model(name=mdl_name),
                    )

                    mv = Model(name=mdl_name, version="latest")
                    assert mv.number == 4
                    artifact = mv.get_artifact(artifact_name)
                    assert artifact.load() == "Hello, World!"
                    assert int(artifact.version) == 5

        finally:
            try:
                Client().delete_artifact(artifact_name)
            except KeyError:
                pass

    def test_link_artifact_via_save_artifact(self):
        """Test that artifacts are auto-linked to a model version on call of `save_artifact`."""
        artifact_name = f"art_{random_str(20)}"
        try:
            with ModelContext(create_model=False) as (mdl_name, _, _):

                @pipeline(
                    enable_cache=False,
                )
                def _inner_pipeline(
                    is_model_artifact: bool = False,
                    is_deployment_artifact: bool = False,
                ):
                    artifact_linker(
                        artifact_name=artifact_name,
                        is_model_artifact=is_model_artifact,
                        is_deployment_artifact=is_deployment_artifact,
                    )

                mv_in_pipe = Model(
                    name=mdl_name,
                )

                # no context, no model
                with patch("zenml.artifacts.utils.logger.debug") as logger:
                    _inner_pipeline()
                    logger.assert_called_once_with(
                        "Unable to link saved artifact to model."
                    )

                # use context
                _inner_pipeline.with_options(model=mv_in_pipe)()

                mv = Model(name=mdl_name, version="latest")
                assert mv.number == 1
                assert mv.get_artifact(artifact_name).load() == "Hello, World!"

                # use context + model
                _inner_pipeline.with_options(model=mv_in_pipe)(
                    is_model_artifact=True
                )

                mv = Model(name=mdl_name, version="latest")
                assert mv.number == 2
                assert (
                    mv.get_model_artifact(artifact_name).load()
                    == "Hello, World!"
                )

                # use context + deployment
                _inner_pipeline.with_options(model=mv_in_pipe)(
                    is_deployment_artifact=True
                )

                mv = Model(name=mdl_name, version="latest")
                assert mv.number == 3
                assert (
                    mv.get_deployment_artifact(artifact_name).load()
                    == "Hello, World!"
                )

                # link outside of a step
                with patch("zenml.artifacts.utils.logger.debug") as logger:
                    save_artifact(data="Hello, World!", name=artifact_name)
                    logger.assert_called_once_with(
                        "Unable to link saved artifact to step run."
                    )
        finally:
            try:
                Client().delete_artifact(artifact_name)
            except KeyError:
                pass

    # TODO: Fix and re-enable this test
    # def test_model_versions_parallel_creation_version_unspecific(
    #     self, clean_client: "Client"
    # ):
    #     """Test that model version creation can be parallelized."""
    #     process_count = 50
    #     args = [
    #         MODEL_NAME,
    #     ] * process_count
    #     with multiprocessing.Pool(5) as pool:
    #         results = pool.map(
    #             parallel_model_version_creation,
    #             iterable=args,
    #         )

    #     assert sum(results), (
    #         "Test was not parallel. "
    #         "Consider increasing the number of processes or pools."
    #     )
    #     assert clean_client.get_model(MODEL_NAME).name == MODEL_NAME
    #     mvs = clean_client.list_model_versions(
    #         model_name_or_id=MODEL_NAME, size=min(1000, process_count * 10)
    #     )
    #     assert len(mvs) == process_count
    #     assert {mv.number for mv in mvs} == {
    #         i for i in range(1, process_count + 1)
    #     }
