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


from unittest.mock import patch

import pytest
import yaml

from zenml import get_step_context, pipeline, step
from zenml.model.model_version import ModelVersion


@step
def assert_model_version_step():
    model_version = get_step_context().model_version
    assert model_version is not None
    assert model_version.name == "foo"
    assert model_version.version == str(model_version.number)
    assert model_version.description == "description"
    assert model_version.license == "MIT"
    assert model_version.audience == "audience"
    assert model_version.use_cases == "use_cases"
    assert model_version.limitations == "limitations"
    assert model_version.trade_offs == "trade_offs"
    assert model_version.ethics == "ethics"
    assert model_version.tags == ["tag"]
    assert model_version.save_models_to_registry


@step
def assert_extra_step():
    extra = get_step_context().pipeline_run.config.extra
    assert extra is not None
    assert extra == {"a": 1}


def test_pipeline_with_model_version_from_yaml(clean_workspace, tmp_path):
    """Test that the pipeline can be configured with a model version from a yaml file."""
    model_version = ModelVersion(
        name="foo",
        description="description",
        license="MIT",
        audience="audience",
        use_cases="use_cases",
        limitations="limitations",
        trade_offs="trade_offs",
        ethics="ethics",
        tags=["tag"],
        save_models_to_registry=True,
    )

    config_path = tmp_path / "config.yaml"
    file_config = dict(
        run_name="run_name_in_file",
        model_version=model_version.dict(),
    )
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=False)
    def assert_model_version_pipeline():
        assert_model_version_step()

    assert_model_version_pipeline.with_options(model_version=model_version)()
    assert_model_version_pipeline.with_options(config_path=str(config_path))()


def test_pipeline_config_from_file_not_overridden_for_extra(
    clean_workspace, tmp_path
):
    """Test that the pipeline can be configured with an extra
    from a yaml file, but the values from yaml are not overridden.
    """
    config_path = tmp_path / "config.yaml"
    file_config = dict(run_name="run_name_in_file", extra={"a": 1})
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=False)
    def assert_extra_pipeline():
        assert_extra_step()

    p = assert_extra_pipeline.with_options(config_path=str(config_path))
    assert p.configuration.extra == {"a": 1}

    with patch("zenml.new.pipelines.pipeline.logger.warning") as warning:
        p.configure(extra={"a": 2})
        warning.assert_called_once()

    assert p.configuration.extra == {"a": 2}

    p()


def test_pipeline_config_from_file_not_overridden_for_model_version(
    clean_workspace, tmp_path
):
    """Test that the pipeline can be configured with a model version
    from a yaml file, but the values from yaml are not overridden.
    """
    initial_model_version = ModelVersion(
        name="bar",
    )

    config_path = tmp_path / "config.yaml"
    file_config = dict(
        run_name="run_name_in_file",
        model_version=initial_model_version.dict(),
    )
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=False)
    def assert_model_version_pipeline():
        assert_model_version_step()

    p = assert_model_version_pipeline.with_options(
        config_path=str(config_path)
    )
    assert p.configuration.model_version.name == "bar"

    with patch("zenml.new.pipelines.pipeline.logger.warning") as warning:
        p.configure(
            model_version=ModelVersion(
                name="foo",
                description="description",
                license="MIT",
                audience="audience",
                use_cases="use_cases",
                limitations="limitations",
                trade_offs="trade_offs",
                ethics="ethics",
                tags=["tag"],
                save_models_to_registry=True,
            )
        )
        warning.assert_called_once()

    assert p.configuration.model_version is not None
    assert p.configuration.model_version.name == "foo"
    assert p.configuration.model_version.version is None
    assert p.configuration.model_version.description == "description"
    assert p.configuration.model_version.license == "MIT"
    assert p.configuration.model_version.audience == "audience"
    assert p.configuration.model_version.use_cases == "use_cases"
    assert p.configuration.model_version.limitations == "limitations"
    assert p.configuration.model_version.trade_offs == "trade_offs"
    assert p.configuration.model_version.ethics == "ethics"
    assert p.configuration.model_version.tags == ["tag"]
    assert p.configuration.model_version.save_models_to_registry
    with pytest.raises(AssertionError):
        p()


def test_pipeline_config_from_file_not_warns_on_new_value(
    clean_workspace, tmp_path
):
    """Test that the pipeline can be configured with an extra
    from a yaml file, but other values are modifiable without warnings.
    """
    config_path = tmp_path / "config.yaml"
    file_config = dict(run_name="run_name_in_file", enable_cache=True)
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=False)
    def assert_extra_pipeline():
        assert_extra_step()

    p = assert_extra_pipeline.with_options(config_path=str(config_path))
    assert p.configuration.extra == {}

    with patch("zenml.new.pipelines.pipeline.logger.warning") as warning:
        p.configure(extra={"a": 1})
        warning.assert_not_called()

    assert p.configuration.extra == {"a": 1}
    assert p.configuration.enable_cache

    p()


@step
def assert_input_params(bar: str):
    assert bar == "bar"


def test_pipeline_config_from_file_works_with_pipeline_parameters(
    clean_workspace, tmp_path
):
    """Test that the pipeline can be configured with parameters
    from a yaml file.
    """
    config_path = tmp_path / "config.yaml"
    file_config = dict(parameters={"foo": "bar"}, enable_cache=False)
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=True)
    def assert_input_params_pipe(foo: str):
        assert_input_params(foo)

    p = assert_input_params_pipe.with_options(config_path=str(config_path))
    assert p.configuration.parameters == {"foo": "bar"}

    # this configuration would be not efficient and overridden by config with warning
    with patch("zenml.new.pipelines.pipeline.logger.warning") as warning:
        p.configure(parameters={"foo": 1})
        warning.assert_called_once()

    assert p.configuration.parameters == {"foo": 1}
    assert not p.configuration.enable_cache

    p()


def test_pipeline_config_from_file_fails_with_pipeline_parameters_on_conflict_with_step_parameters(
    clean_workspace, tmp_path
):
    """Test that the pipeline will fail with error, if configured with parameters
    from a yaml file for the steps and same parameters are passed over in code.
    """
    config_path = tmp_path / "config.yaml"
    file_config = dict(
        parameters={"foo": "bar"},
        steps={
            "assert_input_params": {"parameters": {"bar": 1}}
        },  # here we set `bar` for `assert_input_params`
        enable_cache=False,
    )
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=True)
    def assert_input_params_pipe(foo: str):
        assert_input_params(
            bar=foo
        )  # here we also set `bar` for `assert_input_params`

    p = assert_input_params_pipe.with_options(config_path=str(config_path))
    assert p.configuration.parameters == {"foo": "bar"}

    with pytest.raises(
        RuntimeError,
        match="Configured parameter for the step `assert_input_params` "
        "conflict with parameter passed in runtime",
    ):
        p()


def test_pipeline_config_from_file_fails_with_pipeline_parameters_on_conflict_with_pipeline_parameters(
    clean_workspace, tmp_path
):
    """Test that the pipeline will fail with error, if configured with parameters
    from a yaml file for the steps and same parameters are passed over in code.
    """
    config_path = tmp_path / "config.yaml"
    file_config = dict(
        parameters={"foo": "bar"},
        enable_cache=False,
    )
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=True)
    def assert_input_params_pipe(foo: str):
        assert_input_params(bar=foo)

    p = assert_input_params_pipe.with_options(config_path=str(config_path))
    assert p.configuration.parameters == {"foo": "bar"}

    with pytest.raises(
        RuntimeError,
        match="Configured parameter for the pipeline "
        "`assert_input_params_pipe` conflict with parameter passed in runtime",
    ):
        p(foo="foo")
