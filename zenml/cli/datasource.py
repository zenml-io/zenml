#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import Text

import click
from tabulate import tabulate

from zenml.cli.cli import cli
from zenml.cli.utils import pretty_print, pass_repo
from zenml.repo import Repository


@cli.group()
def datasource():
    """Data source group"""
    pass


@datasource.command("list")
@pass_repo
def list_datasources(repo: Repository):
    datasources = repo.get_datasources()

    click.echo(tabulate([ds.to_config() for ds in datasources],
                        headers="keys"))


@datasource.command("get")
@click.argument('datasource_name')
@pass_repo
def get_datasource_by_name(repo: Repository, datasource_name: Text):
    """
    Gets pipeline from current repository by matching a name identifier
    against the data source name.

    """
    pretty_print(repo.get_datasource_by_name(datasource_name))
