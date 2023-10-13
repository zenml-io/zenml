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


import yaml

from zenml import get_step_context, pipeline, step
from zenml.constants import RUNNING_MODEL_VERSION
from zenml.model import ModelConfig


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
    assert model_config.ethic == "ethic"
    assert model_config.tags == ["tag"]
    assert model_config.version_description == "version_description"
    assert model_config.save_models_to_registry


def test_pipeline_with_model_config_from_yaml(clean_workspace, tmp_path):
    """ """
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
        ethic="ethic",
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
