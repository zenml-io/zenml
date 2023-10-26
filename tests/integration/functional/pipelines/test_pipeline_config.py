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
from zenml.constants import RUNNING_MODEL_VERSION
from zenml.model.model_config import ModelConfig


@step
def assert_model_config_step():
    model_config = get_step_context().model_config
    assert model_config is not None
    assert model_config.name == "foo"
    assert model_config.version == RUNNING_MODEL_VERSION
    assert model_config.create_new_model_version
    assert not model_config.delete_new_version_on_failure
    assert model_config.description == "description"
    assert model_config.license == "MIT"
    assert model_config.audience == "audience"
    assert model_config.use_cases == "use_cases"
    assert model_config.limitations == "limitations"
    assert model_config.trade_offs == "trade_offs"
    assert model_config.ethics == "ethics"
    assert model_config.tags == ["tag"]
    assert model_config.version_description == "version_description"
    assert model_config.save_models_to_registry


@step
def assert_extra_step():
    extra = get_step_context().pipeline_run.config.extra
    assert extra is not None
    assert extra == {"a": 1}


def test_pipeline_with_model_config_from_yaml(clean_workspace, tmp_path):
    """Test that the pipeline can be configured with a model config from a yaml file."""
    model_config = ModelConfig(
        name="foo",
        create_new_model_version=True,
        delete_new_version_on_failure=False,
        description="description",
        license="MIT",
        audience="audience",
        use_cases="use_cases",
        limitations="limitations",
        trade_offs="trade_offs",
        ethics="ethics",
        tags=["tag"],
        version_description="version_description",
        save_models_to_registry=True,
    )

    config_path = tmp_path / "config.yaml"
    file_config = dict(
        run_name="run_name_in_file",
        model_config=model_config.dict(),
    )
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=False)
    def assert_model_config_pipeline():
        assert_model_config_step()

    assert_model_config_pipeline.with_options(model_config=model_config)()
    assert_model_config_pipeline.with_options(config_path=str(config_path))()


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


def test_pipeline_config_from_file_not_overridden_for_model_config(
    clean_workspace, tmp_path
):
    """Test that the pipeline can be configured with a model config
    from a yaml file, but the values from yaml are not overridden.
    """
    initial_model_config = ModelConfig(
        name="bar",
        create_new_model_version=True,
    )

    config_path = tmp_path / "config.yaml"
    file_config = dict(
        run_name="run_name_in_file",
        model_config=initial_model_config.dict(),
    )
    config_path.write_text(yaml.dump(file_config))

    @pipeline(enable_cache=False)
    def assert_model_config_pipeline():
        assert_model_config_step()

    p = assert_model_config_pipeline.with_options(config_path=str(config_path))
    assert p.configuration.model_config.name == "bar"

    with patch("zenml.new.pipelines.pipeline.logger.warning") as warning:
        p.configure(
            model_config=ModelConfig(
                name="foo",
                create_new_model_version=True,
                delete_new_version_on_failure=False,
                description="description",
                license="MIT",
                audience="audience",
                use_cases="use_cases",
                limitations="limitations",
                trade_offs="trade_offs",
                ethics="ethics",
                tags=["tag"],
                version_description="version_description",
                save_models_to_registry=True,
            )
        )
        warning.assert_called_once()

    assert p.configuration.model_config is not None
    assert p.configuration.model_config.name == "foo"
    assert p.configuration.model_config.version == RUNNING_MODEL_VERSION
    assert p.configuration.model_config.create_new_model_version
    assert not p.configuration.model_config.delete_new_version_on_failure
    assert p.configuration.model_config.description == "description"
    assert p.configuration.model_config.license == "MIT"
    assert p.configuration.model_config.audience == "audience"
    assert p.configuration.model_config.use_cases == "use_cases"
    assert p.configuration.model_config.limitations == "limitations"
    assert p.configuration.model_config.trade_offs == "trade_offs"
    assert p.configuration.model_config.ethics == "ethics"
    assert p.configuration.model_config.tags == ["tag"]
    assert (
        p.configuration.model_config.version_description
        == "version_description"
    )
    assert p.configuration.model_config.save_models_to_registry
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
