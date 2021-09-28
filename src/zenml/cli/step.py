# #  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
#
# import click
# from tabulate import tabulate
#
# from zenml.cli.cli import cli
# from zenml.cli.utils import pass_repo
# from zenml.core import Repository
#
#
# @cli.group()
# def step():
#     """Steps group"""
#     pass
#
#
# @step.command("list")
# @pass_repo
# def list_steps(repo: Repository):
#     step_versions = repo.get_step_versions()
#     name_version_data = []
#     headers = ["step_name", "step_version"]
#     for name, version_set in step_versions.items():
#         names = [name] * len(version_set)
#         versions = list(version_set)
#         name_version_data.extend(list(zip(names, versions)))
#
#     click.echo(tabulate(name_version_data, headers=headers))
