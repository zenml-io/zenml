#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Functionality to handle downloading ZenML stacks via the CLI."""

import os
from typing import Any, Dict, List, Optional, Union, cast

import click
from rich.text import Text

from zenml.cli import utils as cli_utils
from zenml.cli.stack import stack
from zenml.constants import (
    ALPHA_MESSAGE,
    STACK_RECIPE_MODULAR_RECIPES,
)
from zenml.io.fileio import rmtree
from zenml.logger import get_logger
from zenml.mlstacks.utils import (
    convert_click_params_to_mlstacks_primitives,
    convert_mlstacks_primitives_to_dicts,
    import_new_stack,
    stack_exists,
    stack_spec_exists,
    verify_spec_and_tf_files_exist,
)
from zenml.recipes import GitStackRecipesHandler
from zenml.utils import yaml_utils
from zenml.utils.analytics_utils import AnalyticsEvent, event_handler
from zenml.utils.io_utils import create_dir_recursive_if_not_exists
from zenml.utils.yaml_utils import write_yaml

logger = get_logger(__name__)


pass_git_stack_recipes_handler = click.make_pass_decorator(
    GitStackRecipesHandler, ensure=True
)


@stack.group(
    "recipe",
    help="Commands for using the stack recipes.",
    invoke_without_command=True,
)
def stack_recipe() -> None:
    """Access all ZenML stack recipes."""


@stack_recipe.command(name="list", help="List the available stack recipes.")
def list_stack_recipes() -> None:
    """List all available stack recipes.

    Args:
        git_stack_recipes_handler: The GitStackRecipesHandler instance.
    """
    cli_utils.warning(ALPHA_MESSAGE)
    stack_recipes = [
        {"stack_recipe_name": stack_recipe_instance}
        for stack_recipe_instance in get_recipe_names()
    ]
    cli_utils.print_table(stack_recipes)

    cli_utils.declare("\n" + "To get the latest list of stack recipes, run: ")
    text = Text("zenml stack recipe pull -y", style="markdown.code_block")
    cli_utils.declare(text)

    cli_utils.declare("\n" + "To pull any individual stack recipe, type: ")
    text = Text(
        "zenml stack recipe pull RECIPE_NAME", style="markdown.code_block"
    )
    cli_utils.declare(text)


@stack_recipe.command(help="Deletes the ZenML stack recipes directory.")
@click.option(
    "--path",
    "-p",
    type=click.STRING,
    default="zenml_stack_recipes",
    help="Relative path at which you want to clean the stack_recipe(s)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Whether to skip the confirmation prompt.",
)
@pass_git_stack_recipes_handler
def clean(
    git_stack_recipes_handler: GitStackRecipesHandler,
    path: str,
    yes: bool,
) -> None:
    """Deletes the stack recipes directory from your working directory.

    Args:
        git_stack_recipes_handler: The GitStackRecipesHandler instance.
        path: The path at which you want to clean the stack_recipe(s).
        yes: Whether to skip the confirmation prompt.
    """
    stack_recipes_directory = os.path.join(os.getcwd(), path)
    if fileio.isdir(stack_recipes_directory) and (
        yes
        or cli_utils.confirmation(
            "Do you wish to delete the stack recipes directory? \n"
            f"{stack_recipes_directory}"
        )
    ):
        git_stack_recipes_handler.clean_current_stack_recipes()
        cli_utils.declare(
            "Stack recipes directory was deleted from your current working "
            "directory."
        )
    elif not fileio.isdir(stack_recipes_directory):
        cli_utils.error(
            f"Unable to delete the stack recipes directory - "
            f"{stack_recipes_directory} - "
            "as it was not found in your current working directory."
        )


@stack_recipe.command(help="Find out more about a stack recipe.")
@click.argument("stack_recipe_name")
def info(
    stack_recipe_name: str,
) -> None:
    """Find out more about a stack recipe.

    Outputs a pager view of the stack_recipe's README.md file.

    Args:
        stack_recipe_name: The name of the stack recipe.
    """
    recipe_readme = cli_utils.get_recipe_readme(stack_recipe_name)
    if recipe_readme is None:
        cli_utils.error(
            f"Unable to find stack recipe {stack_recipe_name}. "
            "Please check the name and try again."
        )
    cli_utils.print_markdown_with_pager(recipe_readme)


@stack_recipe.command(
    help="Describe the stack components and their tools that are "
    "created as part of this recipe."
)
@click.argument("stack_recipe_name")
def describe(
    stack_recipe_name: str,
) -> None:
    """Describe the stack components and their tools that are created as part of this recipe.

    Outputs the "Description" section of the recipe metadata.

    Args:
        stack_recipe_name: The name of the stack recipe.
    """
    stack_recipe_path = cli_utils.get_recipe_path(stack_recipe_name)
    if stack_recipe_path is None:
        cli_utils.error(
            f"Unable to find stack recipe {stack_recipe_name}. "
            "Please check the name and try again."
        )
    recipe_metadata_yaml = os.path.join(stack_recipe_path, "metadata.yaml")
    recipe_metadata = yaml_utils.read_yaml(recipe_metadata_yaml)
    logger.info(recipe_metadata["Description"])


@stack_recipe.command(help="The active version of the mlstacks recipes.")
def version() -> None:
    """The active version of the mlstacks recipes."""
    active_version = cli_utils.get_mlstacks_version()
    if active_version:
        cli_utils.declare(f"Running `mlstacks` version {active_version}.")
    else:
        cli_utils.warning("Unable to detect version.")


@stack.command(help="Deploy a stack using mlstacks.")
@click.option(
    "--provider",
    "-p",
    "provider",
    required=True,
    type=click.Choice(STACK_RECIPE_MODULAR_RECIPES),
)
@click.option(
    "--stack-name",
    "-n",
    "stack_name",
    type=click.STRING,
    required=True,
    help="Set a name for the ZenML stack that will be imported from the YAML "
    "configuration file which gets generated after deploying the stack recipe. "
    "Defaults to the name of the stack recipe being deployed.",
)
@click.option(
    "--region",
    "-r",
    "region",
    type=click.STRING,
    required=True,
    help="The region to deploy the stack to.",
)
@click.option(
    "--import",
    "-i",
    "no_import_stack_flag",
    is_flag=True,
    help="If you don't want the stack to be imported automatically.",
)
@click.option(
    "--artifact-store",
    "-a",
    "artifact_store",
    required=False,
    is_flag=True,
    help="Whether to deploy an artifact store.",
)
@click.option(
    "--container-registry",
    "-c",
    "container_registry",
    required=False,
    is_flag=True,
    help="Whether to deploy a container registry.",
)
@click.option(
    "--mlops-platform",
    "-m",
    "mlops_platform",
    type=click.Choice(["zenml"]),
    required=False,
    help="The flavor of MLOps platform to use."
    "If not specified, the default MLOps platform will be used.",
)
@click.option(
    "--orchestrator",
    "-o",
    required=False,
    type=click.Choice(
        ["kubernetes", "kubeflow", "tekton", "sagemaker", "vertex"]
    ),
    help="The flavor of orchestrator to use. "
    "If not specified, the default orchestrator will be used.",
)
@click.option(
    "--model-deployer",
    "-d",
    "model_deployer",
    required=False,
    type=click.Choice(["kserve", "seldon"]),
    help="The flavor of model deployer to use. ",
)
@click.option(
    "--experiment-tracker",
    "-e",
    "experiment_tracker",
    required=False,
    type=click.Choice(["mlflow"]),
    help="The flavor of experiment tracker to use.",
)
@click.option(
    "--step-operator",
    "-s",
    "step_operator",
    required=False,
    type=click.Choice(["sagemaker"]),
    help="The flavor of step operator to use.",
)
@click.option(  # TODO: handle this case
    "--file",
    "-f",
    "file",
    required=False,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Use a YAML specification file as the basis of the stack deployment.",
)
@click.option(
    "--debug-mode",
    "-b",  # TODO: decide whether this is the best flag to use
    "debug_mode",
    is_flag=True,
    default=False,
    help="Whether to run the stack deployment in debug mode.",
)
@click.option(
    "--extra-config",
    "-x",
    "extra_config",
    multiple=True,
    help="Extra configurations as key=value pairs. This option can be used multiple times.",
)
@click.option(
    "--tags",
    "-t",
    "tags",
    required=False,
    type=click.STRING,
    help="Pass one or more extra configuration values.",
    multiple=True,
)
@click.option(
    "--extra-config",
    "-x",
    "extra_config",
    multiple=True,
    help="Extra configurations as key=value pairs. This option can be used multiple times.",
)
@click.pass_context
def deploy(
    ctx: click.Context,
    provider: str,
    stack_name: str,
    region: str,
    mlops_platform: Optional[str] = None,
    orchestrator: Optional[str] = None,
    model_deployer: Optional[str] = None,
    experiment_tracker: Optional[str] = None,
    step_operator: Optional[str] = None,
    no_import_stack_flag: Optional[bool] = None,
    artifact_store: Optional[bool] = None,
    container_registry: Optional[bool] = None,
    file: Optional[str] = None,
    debug_mode: Optional[bool] = None,
    tags: Optional[List[str]] = None,
    extra_config: Optional[List[str]] = None,
) -> None:
    """Run the stack_recipe at the specified relative path.

    `zenml stack_recipe pull <STACK_RECIPE_NAME>` has to be called with the
    same relative path before the `deploy` command.

    Args:
        ctx: The click context.
        provider: The cloud provider to deploy the stack to.
        force: Force pull the stack recipe, overwriting any existing files.
        stack_name: A name for the ZenML stack that gets imported as a result
            of the recipe deployment.
        no_import_stack_flag: If you don't want the stack to be imported into
            ZenML after deployment.
        artifact_store: The flavor of artifact store to deploy. In the case of
            the artifact store, it doesn't matter what you specify here, as
            there's only one flavor per cloud provider and that will be deployed.
        orchestrator: The flavor of orchestrator to use.
        container_registry: The flavor of container registry to deploy. In the case of
            the container registry, it doesn't matter what you specify here, as
            there's only one flavor per cloud provider and that will be deployed.
        model_deployer: The flavor of model deployer to deploy.
        experiment_tracker: The flavor of experiment tracker to deploy.
        step_operator: The flavor of step operator to deploy.
        extra_config: Extra configurations as key=value pairs.
    """
    # TODO make these checks after the stack spec is created
    # handle at stack level as well as component level
    # delete stack spec if we error out
    if stack_exists(stack_name):
        cli_utils.error(
            f"Stack with name '{stack_name}' already exists. Please choose a "
            "different name."
        )
    elif stack_spec_exists(stack_name):
        cli_utils.error(
            f"Stack spec for stack named '{stack_name}' already exists. "
            "Please choose a different name."
        )

    cli_utils.declare("Checking prerequisites are installed...")
    cli_utils.verify_mlstacks_prerequisites_installation()
    from mlstacks.utils import zenml_utils

    cli_utils.warning(ALPHA_MESSAGE)

    cli_params: Dict[str, Any] = ctx.params
    stack, components = convert_click_params_to_mlstacks_primitives(cli_params)

    cli_utils.declare("Checking flavor compatibility...")
    if not zenml_utils.has_valid_flavor_combinations(stack, components):
        cli_utils.error(
            "The specified stack and component flavors are not compatible "
            "with the provider or with one another. Please try again."
        )

    stack_dict, component_dicts = convert_mlstacks_primitives_to_dicts(
        stack, components
    )
    # write the stack and component yaml files
    from mlstacks.constants import MLSTACKS_PACKAGE_NAME

    spec_dir = (
        f"{click.get_app_dir(MLSTACKS_PACKAGE_NAME)}/stack_specs/{stack.name}"
    )
    cli_utils.declare(f"Writing spec files to {spec_dir}...")
    create_dir_recursive_if_not_exists(spec_dir)

    stack_file_path = f"{spec_dir}/stack-{stack.name}.yaml"
    write_yaml(file_path=stack_file_path, contents=stack_dict)
    for component in component_dicts:
        write_yaml(
            file_path=f"{spec_dir}/{component['name']}.yaml",
            contents=component,
        )

    from mlstacks.utils import terraform_utils

    cli_utils.declare("Deploying stack using Terraform...")
    terraform_utils.deploy_stack(stack_file_path, debug_mode=debug_mode)
    cli_utils.declare("Stack successfully deployed.")

    if not no_import_stack_flag:
        cli_utils.declare(f"Importing stack '{stack_name}' into ZenML...")
        import_new_stack(
            stack_name=stack_name,
            provider=stack.provider,
            stack_spec_dir=spec_dir,
        )
        cli_utils.declare("Stack successfully imported into ZenML.")


@stack.command(
    help="Destroy stack components created previously with "
    "`zenml stack deploy`"
)
@click.argument("stack_name", required=True)
@click.option(
    "--provider",
    "-p",
    "provider",
    type=click.Choice(STACK_RECIPE_MODULAR_RECIPES),
    help="The cloud provider on which the stack is deployed.",
)
@click.option(
    "--debug",
    "-d",
    "debug_mode",
    is_flag=True,
    default=False,
    help="Whether to run Terraform in debug mode.",
)
def destroy(
    stack_name: str,
    provider: str,
    debug_mode: bool = False,
) -> None:
    """Destroy all resources previously created with `zenml stack deploy`."""
    cli_utils.verify_mlstacks_prerequisites_installation()
    from mlstacks.constants import MLSTACKS_PACKAGE_NAME

    # check the stack actually exists
    if not stack_exists(stack_name):
        cli_utils.error(
            f"Stack with name '{stack_name}' does not exist. Please check and "
            "try again."
        )
    spec_files_dir: str = (
        f"{click.get_app_dir(MLSTACKS_PACKAGE_NAME)}/stack_specs/{stack_name}"
    )
    spec_file_path: str = f"{spec_files_dir}/stack-{stack_name}.yaml"
    tf_definitions_path: str = f"{click.get_app_dir(MLSTACKS_PACKAGE_NAME)}/terraform/{provider}-modular"

    cli_utils.declare(
        "Checking Terraform definitions and spec files are present..."
    )
    verify_spec_and_tf_files_exist(spec_file_path, tf_definitions_path)

    from mlstacks.utils import terraform_utils

    cli_utils.declare(f"Destroying stack '{stack_name}' using Terraform...")
    terraform_utils.destroy_stack(
        stack_path=spec_file_path, debug_mode=debug_mode
    )
    cli_utils.declare(f"Stack '{stack_name}' successfully destroyed.")

    if cli_utils.confirmation(
        f"Would you like to recursively delete the associated ZenML "
        f"stack '{stack_name}'?\nThis will delete the stack and any "
        "underlying stack components."
    ):
        from zenml.client import Client

        c = Client()
        c.delete_stack(name_id_or_prefix=stack_name, recursive=True)
        cli_utils.declare(
            f"Stack '{stack_name}' successfully deleted from ZenML."
        )

    spec_dir = os.path.dirname(spec_file_path)
    if cli_utils.confirmation(
        f"Would you like to delete the `mlstacks` spec directory for "
        f"this stack, located at {spec_dir}?"
    ):
        rmtree(spec_files_dir)
        cli_utils.declare(
            f"Spec directory for stack '{stack_name}' successfully deleted."
        )
    cli_utils.declare(f"Stack '{stack_name}' successfully destroyed.")


# a function to get the value of outputs passed as input, from a stack recipe
@stack_recipe.command(
    name="output",
    help="Get a specific output or a list of all outputs from a stack recipe.",
)
@click.argument("stack_recipe_name", type=str)
@click.option(
    "--path",
    "-p",
    type=click.STRING,
    default="zenml_stack_recipes",
    help="Relative path at which you want to install the stack_recipe(s)",
)
@click.option(
    "--output",
    "-o",
    type=click.STRING,
    default=None,
    help="Name of the output you want to get the value of. If none is given,"
    "all outputs are returned.",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
)
def get_outputs(
    stack_recipe_name: str,
    path: str,
    output: Optional[str],
    format: Optional[str],
) -> Union[Dict[str, Any], str]:
    """Get the outputs of the stack recipe at the specified relative path.

    `zenml stack_recipe deploy stack_recipe_name` has to be called from the
    same relative path before the get_outputs command.

    Args:
        git_stack_recipes_handler: The GitStackRecipesHandler instance.
        stack_recipe_name: The name of the stack_recipe.
        path: The path of the stack recipe you want to get the outputs from.
        output: The name of the output you want to get the value of. If none is given,
            all outputs are returned.
        format: The format of the output. If none is given, the output is printed
            to the console.

    Returns:
        One or more outputs of the stack recipe in the specified format.

    Raises:
        ModuleNotFoundError: If the recipe is found at the given path.
    """
    import json

    import yaml

    with event_handler(
        event=AnalyticsEvent.GET_STACK_RECIPE_OUTPUTS,
        metadata={"stack_recipe_name": stack_recipe_name},
    ):
        outputs = cli_utils.get_recipe_outputs(stack_recipe_name, output)
        if output:
            if output in outputs:
                cli_utils.declare(f"Output {output}: ")
                return cast(Dict[str, Any], outputs[output])
            else:
                cli_utils.error(
                    f"Output {output} not found in stack recipe "
                    f"{stack_recipe_name}"
                )
        else:
            cli_utils.declare("Outputs: ")
            # delete all items that have empty values
            outputs = {k: v for k, v in outputs.items() if v != ""}

            if format == "json":
                outputs_json = json.dumps(outputs, indent=4)
                cli_utils.declare(outputs_json)
                return outputs_json
            elif format == "yaml":
                outputs_yaml = yaml.dump(outputs, indent=4)
                cli_utils.declare(outputs_yaml)
                return outputs_yaml
            else:
                cli_utils.declare(str(outputs))
                return outputs
            # except python_terraform.TerraformCommandError as e:
            #     cli_utils.error(str(e))
