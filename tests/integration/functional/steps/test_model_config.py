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

from unittest import mock

import pytest
from tests.integration.functional.utils import model_killer
from typing_extensions import Annotated

from zenml import get_step_context, pipeline, step
from zenml.client import Client
from zenml.constants import RUNNING_MODEL_VERSION
from zenml.model import ArtifactConfig, ModelConfig


@step
def _assert_that_model_config_set(name="foo", version=RUNNING_MODEL_VERSION):
    """Step asserting that passed model name and version is in model context."""
    assert get_step_context().model_config.name == name
    assert get_step_context().model_config.version == version


def test_model_config_passed_to_step_context_via_step():
    """Test that model config was passed to step context via step."""

    @pipeline(name="bar", enable_cache=False)
    def _simple_step_pipeline():
        _assert_that_model_config_set.with_options(
            model_config=ModelConfig(
                name="foo", create_new_model_version=True
            ),
        )()

    with model_killer():
        _simple_step_pipeline()


def test_model_config_passed_to_step_context_via_pipeline():
    """Test that model config was passed to step context via pipeline."""

    @pipeline(
        name="bar",
        model_config=ModelConfig(name="foo", create_new_model_version=True),
        enable_cache=False,
    )
    def _simple_step_pipeline():
        _assert_that_model_config_set()

    with model_killer():
        _simple_step_pipeline()


def test_model_config_passed_to_step_context_via_step_and_pipeline():
    """Test that model config was passed to step context via both, but step is dominating."""

    @pipeline(
        name="bar",
        model_config=ModelConfig(name="bar", create_new_model_version=True),
        enable_cache=False,
    )
    def _simple_step_pipeline():
        _assert_that_model_config_set.with_options(
            model_config=ModelConfig(
                name="foo", create_new_model_version=True
            ),
        )()

    with model_killer():
        _simple_step_pipeline()


def test_model_config_passed_to_step_context_and_switches():
    """Test that model config was passed to step context via both and switches possible."""

    @pipeline(
        name="bar",
        model_config=ModelConfig(name="bar", create_new_model_version=True),
        enable_cache=False,
    )
    def _simple_step_pipeline():
        # this step will use ModelConfig from itself
        _assert_that_model_config_set.with_options(
            model_config=ModelConfig(
                name="foo", create_new_model_version=True
            ),
        )()
        # this step will use ModelConfig from pipeline
        _assert_that_model_config_set(name="bar")
        # and another switch of context
        _assert_that_model_config_set.with_options(
            model_config=ModelConfig(
                name="foobar", create_new_model_version=True
            ),
        )(name="foobar")

    with model_killer():
        _simple_step_pipeline()


@step(model_config=ModelConfig(name="foo", create_new_model_version=True))
def _this_step_creates_a_version():
    return 1


@step
def _this_step_does_not_create_a_version():
    return 1


def test_create_new_versions_both_pipeline_and_step():
    """Test that model config on step and pipeline levels can create new model versions at the same time."""

    @pipeline(
        name="bar",
        model_config=ModelConfig(name="bar", create_new_model_version=True),
        enable_cache=False,
    )
    def _this_pipeline_creates_a_version():
        _this_step_creates_a_version()
        _this_step_does_not_create_a_version()

    with model_killer():
        client = Client()

        _this_pipeline_creates_a_version()

        foo = client.get_model("foo")
        assert foo.name == "foo"
        foo_version = client.get_model_version("foo")
        assert foo_version.version == "1"

        bar = client.get_model("bar")
        assert bar.name == "bar"
        bar_version = client.get_model_version("bar")
        assert bar_version.version == "1"

        _this_pipeline_creates_a_version()

        foo_version = client.get_model_version("foo")
        assert foo_version.version == "2"

        bar_version = client.get_model_version("bar")
        assert bar_version.version == "2"


def test_create_new_version_only_in_step():
    """Test that model config on step level only can create new model version."""

    @pipeline(name="bar", enable_cache=False)
    def _this_pipeline_does_not_create_a_version():
        _this_step_creates_a_version()
        _this_step_does_not_create_a_version()

    with model_killer():
        client = Client()

        _this_pipeline_does_not_create_a_version()

        bar = client.get_model("foo")
        assert bar.name == "foo"
        bar_version = client.get_model_version("foo")
        assert bar_version.version == "1"

        _this_pipeline_does_not_create_a_version()

        bar_version = client.get_model_version("foo")
        assert bar_version.version == "2"


def test_create_new_version_only_in_pipeline():
    """Test that model config on pipeline level only can create new model version."""

    @pipeline(
        name="bar",
        model_config=ModelConfig(name="bar", create_new_model_version=True),
        enable_cache=False,
    )
    def _this_pipeline_creates_a_version():
        _this_step_does_not_create_a_version()

    with model_killer():
        client = Client()

        _this_pipeline_creates_a_version()

        foo = client.get_model("bar")
        assert foo.name == "bar"
        foo_version = client.get_model_version("bar")
        assert foo_version.version == "1"

        _this_pipeline_creates_a_version()

        foo_version = client.get_model_version("bar")
        assert foo_version.version == "2"


@step
def _this_step_produces_output() -> (
    Annotated[int, "data", ArtifactConfig(overwrite=False)]
):
    return 1


@step
def _this_step_tries_to_recover(run_number: int):
    mv = Client().get_model_version(
        model_name_or_id="foo", model_version_name_or_id=RUNNING_MODEL_VERSION
    )
    assert (
        len(mv.artifact_object_ids["data"]) == run_number
    ), "expected AssertionError"

    raise Exception("make pipeline fail")


def test_recovery_of_steps():
    """Test that model config can recover states after previous fails."""

    @pipeline(
        name="bar",
        enable_cache=False,
        model_config=ModelConfig(
            name="foo",
            create_new_model_version=True,
            delete_new_version_on_failure=False,
        ),
    )
    def _this_pipeline_will_recover(run_number: int):
        _this_step_produces_output()
        _this_step_tries_to_recover(
            run_number, after=["_this_step_produces_output"]
        )

    with model_killer():
        client = Client()

        with pytest.raises(Exception, match="make pipeline fail"):
            _this_pipeline_will_recover(1)
        with pytest.raises(Exception, match="make pipeline fail"):
            _this_pipeline_will_recover(2)
        with pytest.raises(Exception, match="make pipeline fail"):
            _this_pipeline_will_recover(3)

        model = client.get_model("foo")
        mv = client.get_model_version(
            model_name_or_id=model.id,
            model_version_name_or_id=RUNNING_MODEL_VERSION,
        )
        assert mv.version == RUNNING_MODEL_VERSION
        assert len(mv.artifact_object_ids) == 1
        assert len(mv.artifact_object_ids["data"]) == 3


def test_clean_up_after_failure():
    """Test that hanging `running` versions are cleaned-up after failure."""

    @pipeline(
        name="bar",
        enable_cache=False,
        model_config=ModelConfig(
            name="foo",
            create_new_model_version=True,
            delete_new_version_on_failure=True,
        ),
    )
    def _this_pipeline_will_not_recover(run_number: int):
        _this_step_produces_output()
        _this_step_tries_to_recover(
            run_number, after=["_this_step_produces_output"]
        )

    with model_killer():
        client = Client()

        with pytest.raises(Exception, match="make pipeline fail"):
            _this_pipeline_will_not_recover(1)
        with pytest.raises(AssertionError, match="expected AssertionError"):
            _this_pipeline_will_not_recover(2)

        model = client.get_model("foo")
        with pytest.raises(KeyError):
            client.get_model_version(
                model_name_or_id=model.id,
                model_version_name_or_id=RUNNING_MODEL_VERSION,
            )


@step(model_config=ModelConfig(name="foo", create_new_model_version=True))
def _new_version_step():
    return 1


@step
def _no_model_config_step():
    return 1


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name="foo", create_new_model_version=True),
)
def _new_version_pipeline_overridden_warns():
    _new_version_step()


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name="foo", create_new_model_version=True),
)
def _new_version_pipeline_not_warns():
    _no_model_config_step()


@pipeline(enable_cache=False)
def _no_new_version_pipeline_not_warns():
    _new_version_step()


@pipeline(enable_cache=False)
def _no_new_version_pipeline_warns_on_steps():
    _new_version_step()
    _new_version_step()


@pipeline(
    enable_cache=False,
    model_config=ModelConfig(name="foo", create_new_model_version=True),
)
def _new_version_pipeline_warns_on_steps():
    _new_version_step()
    _no_model_config_step()


@pytest.mark.parametrize(
    "pipeline, expected_warning",
    [
        (
            _new_version_pipeline_overridden_warns,
            "is overridden in all steps",
        ),
        (_new_version_pipeline_not_warns, ""),
        (_no_new_version_pipeline_not_warns, ""),
        (
            _no_new_version_pipeline_warns_on_steps,
            "`create_new_model_version` is configured only in one",
        ),
        (
            _new_version_pipeline_warns_on_steps,
            "`create_new_model_version` is configured only in one",
        ),
    ],
    ids=[
        "Pipeline with one step, which overrides model_config - warns that pipeline conf is useless.",
        "Configuration in pipeline only - not warns.",
        "Configuration in step only - not warns.",
        "Two steps ask to create new versions - warning to keep it in one place.",
        "Pipeline and one of the steps ask to create new versions - warning to keep it in one place.",
    ],
)
def test_multiple_definitions_create_new_version_warns(
    pipeline, expected_warning
):
    """Test that setting conflicting model configurations are raise warnings to user."""
    with model_killer():
        with mock.patch(
            "zenml.new.pipelines.pipeline.logger.warning"
        ) as logger:
            pipeline()
            if expected_warning:
                logger.assert_called_once()
                assert expected_warning in logger.call_args[0][0]
            else:
                logger.assert_not_called()
