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

import pytest

from zenml import get_step_context, pipeline, step
from zenml.client import Client
from zenml.constants import RUNNING_MODEL_VERSION
from zenml.model.model_config import ModelConfig


@contextmanager
def model_killer(model_name):
    try:
        yield
    finally:
        zs = Client().zen_store
        zs.delete_model(model_name)


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

    with model_killer("foo"):
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

    with model_killer("foo"):
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

    with model_killer("foo"):
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

    with model_killer("foo"):
        with model_killer("bar"):
            with model_killer("foobar"):
                _simple_step_pipeline()


@step(model_config=ModelConfig(name="foo", create_new_model_version=True))
def _this_step_creates_a_version():
    return 1


@step
def _this_step_does_not_create_a_version():
    return 1


def test_create_new_versions_both_pipeline_and_step():
    @pipeline(
        name="bar",
        model_config=ModelConfig(name="bar", create_new_model_version=True),
        enable_cache=False,
    )
    def _this_pipeline_creates_a_version():
        _this_step_creates_a_version()
        _this_step_does_not_create_a_version()

    with model_killer("foo"):
        with model_killer("bar"):
            zs = Client().zen_store
            with pytest.raises(KeyError):
                zs.get_model("foo")
            with pytest.raises(KeyError):
                zs.get_model("bar")

            _this_pipeline_creates_a_version()

            foo = zs.get_model("foo")
            assert foo.name == "foo"
            foo_version = zs.get_model_version("foo")
            assert foo_version.version == "1"

            bar = zs.get_model("bar")
            assert bar.name == "bar"
            bar_version = zs.get_model_version("bar")
            assert bar_version.version == "1"

            _this_pipeline_creates_a_version()

            foo_version = zs.get_model_version("foo")
            assert foo_version.version == "2"

            bar_version = zs.get_model_version("bar")
            assert bar_version.version == "2"


def test_create_new_version_only_in_step():
    @pipeline(name="bar", enable_cache=False)
    def _this_pipeline_does_not_create_a_version():
        _this_step_creates_a_version()
        _this_step_does_not_create_a_version()

    with model_killer("foo"):
        zs = Client().zen_store
        with pytest.raises(KeyError):
            zs.get_model("foo")

        _this_pipeline_does_not_create_a_version()

        bar = zs.get_model("foo")
        assert bar.name == "foo"
        bar_version = zs.get_model_version("foo")
        assert bar_version.version == "1"

        _this_pipeline_does_not_create_a_version()

        bar_version = zs.get_model_version("foo")
        assert bar_version.version == "2"


def test_create_new_version_only_in_pipeline():
    @pipeline(
        name="bar",
        model_config=ModelConfig(name="bar", create_new_model_version=True),
        enable_cache=False,
    )
    def _this_pipeline_creates_a_version():
        _this_step_does_not_create_a_version()

    with model_killer("bar"):
        zs = Client().zen_store
        with pytest.raises(KeyError):
            zs.get_model("bar")

        _this_pipeline_creates_a_version()

        foo = zs.get_model("bar")
        assert foo.name == "bar"
        foo_version = zs.get_model_version("bar")
        assert foo_version.version == "1"

        _this_pipeline_creates_a_version()

        foo_version = zs.get_model_version("bar")
        assert foo_version.version == "2"
