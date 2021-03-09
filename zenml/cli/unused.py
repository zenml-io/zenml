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


def return_pipeline_config_by_id(pipeline_id: Text):
    """
    Utility to get a pipeline object by matching a supplied ID against the
    pipeline YAML configuration associated with it.

    Args:
        pipeline_id: ID of the designated pipeline. Has to be partially
        matching the YAML file name.

    Returns:
        A Pipeline config object built from the matched config

    """
    try:
        repo: Repository = Repository.get_instance()
    except Exception as e:
        error(e)
        return None

    try:
        file_paths = repo.get_pipeline_file_paths()
        path = next(y for y in file_paths if pipeline_id in y)
    except StopIteration:
        error(f"No pipeline matching the identifier {pipeline_id} "
              f"was found.")
        return None

    return read_yaml(path)

    if metadata_store is not None:
        # TODO[MEDIUM]: Figure out how to configure an alternative
        #  metadata store from a command line string
        click.echo("The option to configure the metadata store "
                   "from the command line is not yet implemented.")

    if artifact_store is not None:
        path = artifact_store
        repo.zenml_config.set_artifact_store(artifact_store_path=path)