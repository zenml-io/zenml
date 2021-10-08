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
# """CLI for pipelines."""
#
# import click
# from tabulate import tabulate
#
# from zenml.cli.cli import cli
# from zenml.cli.utils import error, pretty_print, pass_repo
# from zenml.pipelines import TrainingPipeline
# from zenml.core import Repository
# from zenml.utils.yaml_utils import read_yaml
#
#
# @cli.group()
# def pipeline():
#     """Pipeline group"""
#     pass
#
#
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
# @pipeline.command('run')
# @click.argument('path_to_config')
# def run_pipeline(path_to_config: str):
#     """
#     Runs pipeline specified by the given config YAML object.
#
#     Args:
#         path_to_config: Path to config of the designated pipeline.
#          Has to be matching the YAML file name.
#     """
#     # config has metadata store, backends and artifact store,
#     # so no need to specify them
#     print(path_to_config)
#     try:
#         config = read_yaml(path_to_config)
#         p: TrainingPipeline = TrainingPipeline.from_config(config)
#         p.run()
#     except Exception as e:
#         error(e)
