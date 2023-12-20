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

from typing import Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.stack import stack
from zenml.logger import get_logger

logger = get_logger(__name__)


@stack.group(
    "recipe",
    help="DISABLED: Commands for using the stack recipes.",
    invoke_without_command=True,
)
def stack_recipe() -> None:
    """Access all ZenML stack recipes."""


@stack_recipe.command(
    name="list", help="DISABLED: List the available stack recipes."
)
def list_stack_recipes() -> None:
    """List all available stack recipes."""
    cli_utils.warning(
        "This command has been disabled and will be removed in a future "
        "release. Please refer to the `mlstacks` documentation for more "
        "information at https://mlstacks.zenml.io/"
    )


@stack_recipe.command(
    help="DISABLED: Deletes the ZenML stack recipes directory."
)
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
def clean(
    path: str,
    yes: bool,
) -> None:
    """Deletes the stack recipes directory from your working directory.

    Args:
        path: The path at which you want to clean the stack_recipe(s).
        yes: Whether to skip the confirmation prompt.
    """
    cli_utils.warning(
        "This command has been disabled and will be removed in a future "
        "release. Please refer to the `mlstacks` documentation for more "
        "information at https://mlstacks.zenml.io/"
    )


@stack_recipe.command(help="DISABLED: Find out more about a stack recipe.")
@click.argument("stack_recipe_name")
def info(
    stack_recipe_name: str,
) -> None:
    """Find out more about a stack recipe.

    Outputs a pager view of the stack_recipe's README.md file.

    Args:
        stack_recipe_name: The name of the stack recipe.
    """
    cli_utils.warning(
        "This command has been disabled and will be removed in a future "
        "release. Please refer to the `mlstacks` documentation for more "
        "information at https://mlstacks.zenml.io/"
    )


@stack_recipe.command(
    help="DISABLED: Describe the stack components for a recipe."
)
@click.argument(
    "stack_recipe_name",
    type=click.Choice(("aws-modular", "gcp-modular", "k3d-modular")),
)
def describe(
    stack_recipe_name: str,
) -> None:
    """Describe the stack components and their tools.

    Outputs the "Description" section of the recipe metadata.

    Args:
        stack_recipe_name: The name of the stack recipe.
    """
    cli_utils.warning(
        "This command has been disabled and will be removed in a future "
        "release. Please refer to the `mlstacks` documentation for more "
        "information at https://mlstacks.zenml.io/"
    )


@stack_recipe.command(help="DISABLED: Pull stack recipes.")
@click.argument("stack_recipe_name", required=False, default=None)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the redownload of the stack_recipes folder to the ZenML config "
    "folder.",
)
@click.option(
    "--path",
    "-p",
    type=click.STRING,
    default="zenml_stack_recipes",
    help="Relative path at which you want to install the stack recipe(s)",
)
def pull(
    stack_recipe_name: str,
    force: bool,
    path: str,
) -> None:
    """Pull stack_recipes straight into your current working directory.

    Add the flag --yes or -y to redownload all the stack_recipes afresh.

    Args:
        stack_recipe_name: The name of the stack_recipe.
        force: Force the redownload of the stack_recipes folder.
        path: The path at which you want to install the stack_recipe(s).
    """
    cli_utils.warning(
        "This command has been disabled and will be removed in a future "
        "release. Please refer to the `mlstacks` documentation for more "
        "information at https://mlstacks.zenml.io/"
    )


@stack_recipe.command(help="DISABLED: Deploy a stack recipe.")
@click.argument("stack_recipe_name", required=True)
@click.option(
    "--path",
    "-p",
    type=click.STRING,
    default="zenml_stack_recipes",
    help="Relative path at which local stack recipe(s) should exist",
)
@click.option(
    "--force",
    "-f",
    "force",
    is_flag=True,
    help="Force pull the stack recipe. This overwrites any existing recipe "
    "files present locally, including the terraform state files and the "
    "local configuration.",
)
@click.option(
    "--stack-name",
    "-n",
    type=click.STRING,
    required=False,
    help="Set a name for the ZenML stack that will be imported from the YAML "
    "configuration file which gets generated after deploying the stack recipe. "
    "Defaults to the name of the stack recipe being deployed.",
)
@click.option(
    "--import",
    "import_stack_flag",
    is_flag=True,
    help="Import the stack automatically after the recipe is deployed.",
)
@click.option(
    "--log-level",
    type=click.Choice(
        ["TRACE", "DEBUG", "INFO", "WARN", "ERROR"], case_sensitive=False
    ),
    help="Choose one of TRACE, DEBUG, INFO, WARN or ERROR (case insensitive) as "
    "log level for the deploy operation.",
    default="ERROR",
)
@click.option(
    "--no-server",
    is_flag=True,
    help="Don't deploy ZenML even if there's no active cloud deployment.",
)
@click.option(
    "--skip-pull",
    is_flag=True,
    help="Skip the pulling of the stack recipe before deploying. This should be used "
    "if you have a local copy of your recipe already. Use the `--path` or `-p` flag to "
    "specify the directory that hosts your recipe(s).",
)
@click.option(
    "--artifact-store",
    "-a",
    help="The flavor of artifact store to use. "
    "If not specified, the default artifact store will be used.",
)
@click.option(
    "--orchestrator",
    "-o",
    help="The flavor of orchestrator to use. "
    "If not specified, the default orchestrator will be used.",
)
@click.option(
    "--container-registry",
    "-c",
    help="The flavor of container registry to use. "
    "If not specified, no container registry will be deployed.",
)
@click.option(
    "--model-deployer",
    "-d",
    help="The flavor of model deployer to use. "
    "If not specified, no model deployer will be deployed.",
)
@click.option(
    "--experiment-tracker",
    "-e",
    help="The flavor of experiment tracker to use. "
    "If not specified, no experiment tracker will be deployed.",
)
@click.option(
    "--step-operator",
    "-s",
    help="The flavor of step operator to use. "
    "If not specified, no step operator will be deployed.",
)
@click.option(
    "--config",
    help="Use a YAML or JSON configuration or configuration file to pass"
    "variables to the stack recipe.",
    required=False,
    type=str,
)
@click.pass_context
def deploy(
    ctx: click.Context,
    stack_recipe_name: str,
    artifact_store: Optional[str],
    orchestrator: Optional[str],
    container_registry: Optional[str],
    model_deployer: Optional[str],
    experiment_tracker: Optional[str],
    step_operator: Optional[str],
    path: str,
    force: bool,
    import_stack_flag: bool,
    log_level: str,
    no_server: bool,
    skip_pull: bool,
    stack_name: Optional[str],
    config: Optional[str],
) -> None:
    """Run the stack_recipe at the specified relative path.

    `zenml stack_recipe pull <STACK_RECIPE_NAME>` has to be called with the
    same relative path before the `deploy` command.

    Args:
        ctx: The click context.
        stack_recipe_name: The name of the stack_recipe.
        path: The path at which you want to install the stack_recipe(s).
        force: Force pull the stack recipe, overwriting any existing files.
        stack_name: A name for the ZenML stack that gets imported as a result
            of the recipe deployment.
        import_stack_flag: Import the stack automatically after the recipe is
            deployed. The stack configuration file is always generated and
            can be imported manually otherwise.
        log_level: Choose one of TRACE, DEBUG, INFO, WARN or ERROR
            (case-insensitive) as log level for the `deploy` operation.
        no_server: Don't deploy ZenML even if there's no active cloud
            deployment.
        skip_pull: Skip the pull of the stack recipe before deploying. This
            should be used if you have a local copy of your recipe already.
        artifact_store: The flavor of artifact store to deploy. In the case of
            the artifact store, it doesn't matter what you specify here, as
            there's only one flavor per cloud provider and that will be
            deployed.
        orchestrator: The flavor of orchestrator to use.
        container_registry: The flavor of container registry to deploy.
            In the case of the container registry, it doesn't matter what you
            specify here, as there's only one flavor per cloud provider and
            that will be deployed.
        model_deployer: The flavor of model deployer to deploy.
        experiment_tracker: The flavor of experiment tracker to deploy.
        step_operator: The flavor of step operator to deploy.
        config: Use a YAML or JSON configuration or configuration file to pass
            variables to the stack recipe.
    """
    cli_utils.warning(
        "This command has been disabled and will be removed in a future "
        "release. Please use `zenml stack deploy ...` instead. For more "
        "information and to learn about the new syntax, please refer to "
        "the `mlstacks` documentation at https://mlstacks.zenml.io/"
    )


@stack_recipe.command(help="DISABLED: Destroy stack components")
@click.argument("stack_recipe_name", required=True)
@click.option(
    "--path",
    "-p",
    type=click.STRING,
    default="zenml_stack_recipes",
    help="Relative path at which you want to install the stack_recipe(s)",
)
@click.option(
    "--artifact-store",
    "-a",
    help="The flavor of artifact store to destroy. "
    "If not specified, the default artifact store will be assumed.",
)
@click.option(
    "--orchestrator",
    "-o",
    help="The flavor of orchestrator to destroy. "
    "If not specified, the default orchestrator will be used.",
)
@click.option(
    "--container-registry",
    "-c",
    help="The flavor of container registry to destroy. "
    "If not specified, no container registry will be destroyed.",
)
@click.option(
    "--model-deployer",
    "-d",
    help="The flavor of model deployer to destroy. "
    "If not specified, no model deployer will be destroyed.",
)
@click.option(
    "--experiment-tracker",
    "-e",
    help="The flavor of experiment tracker to destroy. "
    "If not specified, no experiment tracker will be destroyed.",
)
@click.option(
    "--step-operator",
    "-s",
    help="The flavor of step operator to destroy. "
    "If not specified, no step operator will be destroyed.",
)
def destroy(
    stack_recipe_name: str,
    path: str,
    artifact_store: Optional[str],
    orchestrator: Optional[str],
    container_registry: Optional[str],
    model_deployer: Optional[str],
    experiment_tracker: Optional[str],
    step_operator: Optional[str],
) -> None:
    """Destroy all resources.

    `zenml stack_recipe deploy stack_recipe_name` has to be called with the
    same relative path before the destroy command. If you want to destroy
    specific components of the stack, you can specify the component names
    with the corresponding options. If no component is specified, all
    components will be destroyed.

    Args:
        stack_recipe_name: The name of the stack_recipe.
        path: The path of the stack recipe you want to destroy.
        artifact_store: The flavor of the artifact store to destroy.
            In the case of the artifact store, it doesn't matter what you
            specify here, as there's only one flavor per cloud provider and
            that will be destroyed.
        orchestrator: The flavor of the orchestrator to destroy.
        container_registry: The flavor of the container registry to destroy.
            In the case of the container registry, it doesn't matter what you
            specify here, as there's only one flavor per cloud provider and
            that will be destroyed.
        model_deployer: The flavor of the model deployer to destroy.
        experiment_tracker: The flavor of the experiment tracker to destroy.
        step_operator: The flavor of the step operator to destroy.
    """
    cli_utils.warning(
        "This command has been disabled and will be removed in a future "
        "release. Please use `zenml stack destroy ...` instead. For more "
        "information and to learn about the new syntax, please refer to "
        "the `mlstacks` documentation at https://mlstacks.zenml.io/"
    )


@stack_recipe.command(
    name="output",
    help="DISABLED: Get outputs from a stack recipe.",
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
) -> None:
    """Get the outputs of the stack recipe at the specified relative path.

    `zenml stack_recipe deploy stack_recipe_name` has to be called from the
    same relative path before the get_outputs command.

    Args:
        stack_recipe_name: The name of the stack_recipe.
        path: The path of the stack recipe you want to get the outputs from.
        output: The name of the output you want to get the value of.
            If none is given, all outputs are returned.
        format: The format of the output. If none is given, the output
            is printed to the console.
    """
    cli_utils.warning(
        "This command has been disabled and will be removed in a future "
        "release. For more information and to learn about the new syntax, "
        "please refer to the `mlstacks` documentation at "
        "https://mlstacks.zenml.io/"
    )


@stack_recipe.command(help="DISABLED: The active version of mlstacks recipes.")
def version() -> None:
    """The active version of the mlstacks recipes."""
    cli_utils.warning(
        "This command has been disabled and will be removed in a future "
        "release. For more information and to learn about the new syntax, "
        "please refer to the `mlstacks` documentation at "
        "https://mlstacks.zenml.io/"
    )
