# #  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
# #
# #  Licensed under the Apache License, Version 2.0 (the "License");
# #  you may not use this file except in compliance with the License.
# #  You may obtain a copy of the License at:
# #
# #       http://www.apache.org/licenses/LICENSE-2.0
# #
# #  Unless required by applicable law or agreed to in writing, software
# #  distributed under the License is distributed on an "AS IS" BASIS,
# #  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# #  or implied. See the License for the specific language governing
# #  permissions and limitations under the License.
"""CLI to interact with pipelines."""
import importlib
import os
import sys
import types
from typing import Any

import click

from zenml.cli.cli import cli
from zenml.exceptions import PipelineConfigurationError
from zenml.logger import get_logger
from zenml.utils import yaml_utils

logger = get_logger(__name__)


def _import_python_file(file_path: str) -> types.ModuleType:
    """Imports a python file.

    Args:
        file_path: Path to python file that should be imported.

    Returns:
        The imported module.
    """
    # Add directory of python file to PYTHONPATH so we can import it
    file_path = os.path.abspath(file_path)
    sys.path.append(os.path.dirname(file_path))

    module_name = os.path.splitext(os.path.basename(file_path))[0]
    return importlib.import_module(module_name)


def _get_module_attribute(module: types.ModuleType, attribute_name: str) -> Any:
    """Gets an attribute from a module.

    Args:
        module: The module to load the attribute from.
        attribute_name: Name of the attribute to load.

    Returns:
        The attribute value.

    Raises:
        PipelineConfigurationError: If the module does not have an attribute
            with the given name.
    """
    try:
        return getattr(module, attribute_name)
    except AttributeError:
        raise PipelineConfigurationError(
            f"Unable to load '{attribute_name}' from"
            f" file '{module.__file__}'"
        ) from None


@cli.group()
def pipeline() -> None:
    """Pipeline group"""


@pipeline.command("run", help="Run a pipeline with the given configuration.")
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
)
@click.argument("python_file")
def run_pipeline(python_file: str, config_path: str) -> None:
    """Runs pipeline specified by the given config YAML object.

    Args:
        python_file: Path to the python file that defines the pipeline.
        config_path: Path to configuration YAML file.
    """
    module = _import_python_file(python_file)
    config = yaml_utils.read_yaml(config_path)

    pipeline_name = config["name"]
    pipeline_class = _get_module_attribute(module, pipeline_name)

    steps = {}
    for step_name, step_config in config["steps"].items():
        step_class = _get_module_attribute(module, step_config["source"])
        step_instance = step_class()
        materializers_config = step_config.get("materializers", None)
        if materializers_config:
            # We need to differentiate whether it's a single materializer
            # or a dictionary mapping output names to materializers
            if isinstance(materializers_config, str):
                materializers = _get_module_attribute(
                    module, materializers_config
                )
            elif isinstance(materializers_config, dict):
                materializers = {
                    output_name: _get_module_attribute(module, source)
                    for output_name, source in materializers_config.items()
                }
            else:
                raise PipelineConfigurationError(
                    f"Only `str` and `dict` values are allowed for "
                    f"'materializers' attribute of a step configuration. You "
                    f"tried to pass in `{materializers_config}` (type: "
                    f"`{type(materializers_config).__name__}`)."
                )
            step_instance = step_instance.with_return_materializers(
                materializers
            )

        steps[step_name] = step_instance

    pipeline_instance = pipeline_class(**steps).with_config(
        config_path, overwrite_step_parameters=True
    )
    logger.debug("Finished setting up pipeline '%s' from CLI", pipeline_name)
    pipeline_instance.run()
