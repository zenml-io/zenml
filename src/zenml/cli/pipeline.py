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


import click

from zenml.cli.cli import cli


@cli.group()
def pipeline() -> None:
    """Pipeline group"""


# @pipeline.command('compare')
# @pass_repo
# def compare_training_runs(repo: Repository):
#     """Compares pipelines in repo"""
#     click.echo('Comparing training pipelines in repo: Starting app..')
#     repo.compare_training_runs()
#
#
# @pipeline.command('list')
# @pass_repo
# def list_pipelines(repo: Repository):
#     """Lists pipelines in the current repository."""
#     try:
#         pipelines = repo.get_pipelines()
#
#         names = [p.name for p in pipelines]
#         types = [p.PIPELINE_TYPE for p in pipelines]
#         statuses = [p.get_status() for p in pipelines]
#         cache_enabled = [p.enable_cache for p in pipelines]
#         filenames = [p.file_name for p in pipelines]
#
#         headers = ["name", "type", "cache enabled", "status", "file name"]
#
#         click.echo(tabulate(zip(names, types, cache_enabled,
#                                 statuses, filenames),
#                             headers=headers))
#     except Exception as e:
#         error(e)
#
#
# @pipeline.command('get')
# @click.argument('pipeline_name')
# @pass_repo
# def get_pipeline_by_name(repo: Repository, pipeline_name: str):
#     """
#     Gets pipeline from current repository by matching a name against a
#     pipeline name in the repository.
#     """
#     try:
#         p = repo.get_pipeline_by_name(pipeline_name)
#     except Exception as e:
#         error(e)
#         return
#
#     pretty_print(p)
#
#


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
    import importlib
    import os
    import sys

    from zenml.utils import yaml_utils

    python_file = os.path.abspath(python_file)

    # Add directory of python file to PYTHONPATH so we can import it
    sys.path.append(os.path.dirname(python_file))

    module_name = os.path.splitext(os.path.basename(python_file))[0]
    pipeline_module = importlib.import_module(module_name)

    config = yaml_utils.read_yaml(config_path)

    pipeline_name = config["name"]
    pipeline_class = getattr(pipeline_module, pipeline_name)

    steps = {}
    for step_name, step_config in config["steps"].items():
        step_class = getattr(pipeline_module, step_config["source"])
        step_instance = step_class()
        materializers_config = step_config.get("materializers", None)
        if isinstance(materializers_config, str):
            # Single materializer
            materializer = getattr(pipeline_module, materializers_config)
            step_instance = step_instance.with_return_materializers(
                materializer
            )
        elif isinstance(materializers_config, dict):
            materializers = {}
            for (
                output_name,
                materializer_source,
            ) in materializers_config.items():
                materializers[output_name] = getattr(
                    pipeline_module, materializer_source
                )
            step_instance = step_instance.with_return_materializers(
                materializers
            )

        steps[step_name] = step_instance

    pipeline_instance = pipeline_class(**steps).with_config(
        config_path, overwrite_step_parameters=True
    )
    pipeline_instance.run()
