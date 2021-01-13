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

import click
from tabulate import tabulate
from zenml.cli.cli import cli
from zenml.cli.utils import error, parse_unknown_options
from zenml.core.repo.repo import Repository
from zenml.core.datasources.bq_datasource import BigQueryDatasource
from zenml.core.datasources.image_datasource import ImageDatasource
from zenml.core.datasources.csv_datasource import CSVDatasource


@cli.group()
def datasource():
    """Data source group"""
    pass


@datasource.command("list")
def list_datasources():
    try:
        repo: Repository = Repository.get_instance()
    except Exception as e:
        error(e)
        return

    datasources = repo.get_datasources()

    click.echo(tabulate([ds.to_config() for ds in datasources],
                        headers="keys"))


@datasource.command("get")
@click.argument('datasource_name')
def get_datasource_by_name(datasource_name):
    """
    Gets pipeline from current repository by matching a name identifier
    against the data source name.

    """
    try:
        repo: Repository = Repository.get_instance()
    except Exception as e:
        error(e)
        return

    click.echo(str(repo.get_datasource_by_name(datasource_name)))


@datasource.command("create")
@click.argument('type', nargs=1)
@click.argument("name", nargs=1)
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def create_datasource(type, name, args):
    """
    Creates a datasource in the current repository of the given type
    with the given name and args.

    Args:
        type: Type of the datasource to create.
        name: Name of the datasource in the repo.
        args: Constructor arguments necessary for creating the chosen
        datasource.

    """
    # TODO[HIGH]: Hardcoded, better to instantiate a datasource factory in
    #  the datasource click group
    source_dict = {"bq": BigQueryDatasource,
                   "csv": CSVDatasource,
                   "image": ImageDatasource,
                   }

    if type.lower() not in source_dict:
        error("Unknown datasource type was given. Available types are: "
              "{}".format(",".join(k for k in source_dict.keys())))

    try:
        source_args = parse_unknown_options(args)
        ds = source_dict.get(type.lower())(name=name, **source_args)
    except Exception as e:
        error(e)
        return
