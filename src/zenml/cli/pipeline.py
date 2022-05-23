#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
"""CLI to interact with pipelines."""
import os.path
import textwrap
import types
from typing import Any, Dict

import click

from zenml.cli.cli import TagGroup, cli
from zenml.config.config_keys import (
    PipelineConfigurationKeys,
    SourceConfigurationKeys,
    StepConfigurationKeys,
)
from zenml.enums import CliCategories
from zenml.exceptions import PipelineConfigurationError
from zenml.logger import get_logger
from zenml.utils import source_utils, yaml_utils

logger = get_logger(__name__)


def _load_class_from_module(
    module: types.ModuleType, config_item: Dict[str, str]
) -> Any:
    """Based on a config item from the config yaml the corresponding module
    attribute is loaded.

    Args:
        module: Base module to use for import if only a function/class name is
                supplied
        config_item: Config item loaded from the config yaml
                        - it will have a function/class name and
                        optionally a relative filepath
                        (e.g {`file`: `steps/steps.py`, `name`: `step_name`}

    Returns:
         imported function/class
    """
    if isinstance(config_item, dict):
        if SourceConfigurationKeys.FILE_ in config_item:
            module = source_utils.import_python_file(
                config_item[SourceConfigurationKeys.FILE_]
            )

        implementation_name = config_item[SourceConfigurationKeys.NAME_]
        implemented_class = _get_module_attribute(module, implementation_name)
        return implemented_class
    else:
        correct_input = textwrap.dedent(
            f"""
        {SourceConfigurationKeys.NAME_}: ClassName
        {SourceConfigurationKeys.FILE_}: optional/filepath.py
        """
        )
        raise PipelineConfigurationError(
            "Only `dict` values are allowed for "
            "'step_source' attribute of a step configuration. You "
            f"tried to pass in `{config_item}` (type: "
            f"`{type(config_item).__name__}`). \n"
            "You will now need to pass a dictionary. This dictionary "
            f"**has to** contain a `{SourceConfigurationKeys.NAME_}` which "
            "refers to the function/class name. If this entity is defined "
            "outside the main module, you will need to additionally supply a "
            f"{SourceConfigurationKeys.FILE_} with the relative forward-slash-"
            "separated path to the file. \n"
            "A correct configuration would look a bit like this:"
            f"{correct_input}"
        )


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


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def pipeline() -> None:
    """Run pipelines."""


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
    # If the file was run with `python run.py, this would happen automatically.
    #  In order to allow seamless switching between running directly and through
    #  zenml, this is done at this point
    with source_utils.prepend_python_path(
        os.path.abspath(os.path.dirname(python_file))
    ):

        module = source_utils.import_python_file(python_file)
        config = yaml_utils.read_yaml(config_path)
        PipelineConfigurationKeys.key_check(config)

        pipeline_name = config[PipelineConfigurationKeys.NAME]
        pipeline_class = _get_module_attribute(module, pipeline_name)

        steps = {}
        for step_name, step_config in config[
            PipelineConfigurationKeys.STEPS
        ].items():
            StepConfigurationKeys.key_check(step_config)
            source = step_config[StepConfigurationKeys.SOURCE_]
            step_class = _load_class_from_module(module, source)

            step_instance = step_class()
            materializers_config = step_config.get(
                StepConfigurationKeys.MATERIALIZERS_, None
            )
            if materializers_config:
                # We need to differentiate whether it's a single materializer
                # or a dictionary mapping output names to materializers
                if isinstance(materializers_config, str):
                    correct_input = textwrap.dedent(
                        f"""
                    {SourceConfigurationKeys.NAME_}: {materializers_config}
                    {SourceConfigurationKeys.FILE_}: optional/filepath.py
                    """
                    )

                    raise PipelineConfigurationError(
                        "As of ZenML version 0.8.0 `str` entries are no "
                        "longer supported "
                        "to define steps or materializers. Instead you will "
                        "now need to "
                        "pass a dictionary. This dictionary **has to** "
                        "contain a "
                        f"`{SourceConfigurationKeys.NAME_}` which refers to "
                        f"the function/"
                        "class name. If this entity is defined outside the "
                        "main module,"
                        "you will need to additionally supply a "
                        f"{SourceConfigurationKeys.FILE_} with the relative "
                        f"forward-slash-"
                        "separated path to the file. \n"
                        f"You tried to pass in `{materializers_config}` "
                        f"- however you should have specified the name "
                        f"(and file) like this: \n "
                        f"{correct_input}"
                    )
                elif isinstance(materializers_config, dict):
                    materializers = {
                        output_name: _load_class_from_module(module, source)
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
        logger.debug(
            "Finished setting up pipeline '%s' from CLI", pipeline_name
        )
        pipeline_instance.run()
