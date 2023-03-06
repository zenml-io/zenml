#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""CLI functionality to interact with the ZenML Hub."""
import os
import shutil
import subprocess
import sys
from importlib.util import find_spec
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import click
import requests
from git.repo import Repo
from pydantic import BaseModel, ValidationError

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import declare, error, print_table
from zenml.enums import CliCategories
from zenml.hub.config import get_settings
from zenml.logger import get_logger

logger = get_logger(__name__)


Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class PluginBaseModel(BaseModel):
    """Base model for a plugin."""

    name: str
    version: Optional[str]
    release_notes: Optional[str]
    repository_url: str
    repository_subdirectory: Optional[str]
    repository_branch: Optional[str]
    repository_commit: Optional[str]
    tags: Optional[str]  # TODO: make this a list?


class PluginRequestModel(PluginBaseModel):
    """Request model for a plugin."""


class PluginResponseModel(PluginBaseModel):
    """Response model for a plugin."""

    status: Optional[str]  # TODO: make this a required enum
    version: str
    index_url: Optional[str]
    wheel_name: Optional[str]  # TODO: rename to package_name?
    logo: Optional[str]
    requirements: Optional[List[str]]


def _hub_request(
    method: str, url: str, data: Optional[str] = None
) -> Optional[Json]:
    """Helper function to make a request to the hub."""
    session = requests.Session()

    # Define headers
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    auth_token = get_settings().AUTH_TOKEN
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    # Make the request
    response = session.request(
        method=method,
        url=url,
        data=data,
        headers=headers,
        params={},
        verify=False,
        timeout=30,
    )

    # Parse and return the response
    payload: Json = response.json() if response else None
    return payload


def _hub_get(url: str) -> Optional[Json]:
    """Helper function to make a GET request to the hub."""
    return _hub_request("GET", url)


def _hub_post(url: str, model: PluginRequestModel) -> Optional[Json]:
    """Helper function to make a POST request to the hub."""
    return _hub_request("POST", url, data=model.json())


def _list_plugins() -> List[PluginResponseModel]:
    """Helper function to list all plugins in the hub."""
    payload = _hub_get(f"{get_settings().SERVER_URL}/plugins")
    if not isinstance(payload, list):
        return []
    return [PluginResponseModel.parse_obj(plugin) for plugin in payload]


def _get_plugin(
    plugin_name: str, plugin_version: Optional[str] = None
) -> Optional[PluginResponseModel]:
    """Helper function to get a specfic plugin from the hub."""
    url = f"{get_settings().SERVER_URL}/plugins/{plugin_name}"
    if plugin_version:
        url += f"?version={plugin_version}"

    payload = _hub_get(url)

    try:
        return PluginResponseModel.parse_obj(payload)
    except ValidationError:
        return None


def _create_plugin(
    plugin_request: PluginRequestModel, is_new_version: bool
) -> PluginResponseModel:
    """Helper function to create a plugin in the hub."""
    url = f"{get_settings().SERVER_URL}/plugins"
    if is_new_version:
        url += f"/{plugin_request.name}/versions"

    payload = _hub_post(url, plugin_request)

    try:
        return PluginResponseModel.parse_obj(payload)
    except ValidationError:
        raise RuntimeError(
            f"Failed to create plugin {plugin_request.name}: {payload}"
        )


def _stream_plugin_build_logs(plugin_name: str, plugin_version: str) -> None:
    """Helper function to stream the build logs of a plugin."""
    logs_url = (
        f"{get_settings().SERVER_URL}/plugins/{plugin_name}/versions/"
        f"{plugin_version}/logs"
    )
    found_logs = False
    with requests.get(logs_url, stream=True) as response:
        for line in response.iter_lines(chunk_size=None, decode_unicode=True):
            found_logs = True
            if line.startswith("Build failed"):
                error(line)
            else:
                logger.info(line)

    if not found_logs:
        logger.info(f"No logs found for plugin {plugin_name}:{plugin_version}")


def _is_plugin_installed(plugin_name: str) -> bool:
    """Helper function to check if a plugin is installed."""
    # TODO: we need to determine this based on the package name, not based on
    # the import path (which is not always the same and can be defined by
    # multiple plugins)
    spec = find_spec(f"zenml.hub.{plugin_name}")
    return spec is not None


def _format_plugins_table(
    plugins: List[PluginResponseModel],
) -> List[Dict[str, str]]:
    """Helper function to format a list of plugins into a table."""
    plugins_table = []
    for plugin in plugins:
        if _is_plugin_installed(plugin.name):
            installed_icon = ":white_check_mark:"
        else:
            installed_icon = ":x:"
        plugins_table.append({"INSTALLED": installed_icon, **plugin.dict()})
    return plugins_table


def _plugin_display_name(plugin_name: str, version: Optional[str]) -> str:
    """Helper function to get the display name of a plugin.

    Args:
        plugin_name: Name of the plugin.
        version: Version of the plugin.

    Returns:
        Display name of the plugin.
    """
    if version:
        return f"{plugin_name}:{version}"
    return f"{plugin_name}:latest"


@cli.group(cls=TagGroup, tag=CliCategories.HUB)
def hub() -> None:
    """Interact with the ZenML Hub."""


@hub.command("list")
def list_plugins() -> None:
    """List all plugins available on the hub."""
    plugins = _list_plugins()
    if not plugins:
        declare("No plugins found.")
    plugins_table = _format_plugins_table(plugins)
    print_table(plugins_table)


@hub.command("install")
@click.argument("plugin_name", type=str, required=True)
@click.option(
    "--version",
    "-v",
    type=str,
    help="Version of the plugin to install.",
)
@click.option(
    "--no-deps",
    "--no-dependencies",
    is_flag=True,
    help="Do not install dependencies of the plugin.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Do not ask for confirmation before installing.",
)
def install_plugin(
    plugin_name: str,
    version: Optional[str] = None,
    no_deps: bool = False,
    yes: bool = False,
) -> None:
    """Install a plugin from the hub."""
    display_name = _plugin_display_name(plugin_name, version)

    # Get plugin from hub
    plugin = _get_plugin(plugin_name, version)
    if not plugin:
        error(f"Could not find plugin '{display_name}' on the hub.")

    # Check if plugin can be installed
    index_url = plugin.index_url
    wheel_name = plugin.wheel_name
    if not index_url or not wheel_name:
        error(f"Plugin '{display_name}' is not available for installation.")

    # Install plugin dependencies
    if not no_deps and plugin.requirements:
        requirements_str = " ".join(f"'{r}'" for r in plugin.requirements)

        if not yes:
            confirmation = click.confirm(
                f"Plugin '{display_name}' requires the following "
                f"packages to be installed: {requirements_str}. Do you want to "
                f"install them now?"
            )
            if not confirmation:
                error(
                    f"Plugin '{display_name}' cannot be installed "
                    "without the required packages."
                )

        logger.info(
            f"Installing requirements for plugin '{display_name}': "
            f"{requirements_str}..."
        )
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *plugin.requirements]
        )
        logger.info(
            f"Successfully installed requirements for plugin "
            f"'{display_name}'."
        )

    # pip install the wheel
    logger.info(
        f"Installing plugin '{display_name}' from "
        f"{index_url}{wheel_name}..."
    )
    install_call = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--index-url",
        index_url,
        wheel_name,
    ]
    if no_deps:
        install_call.append("--no-deps")
    subprocess.check_call(install_call)
    logger.info(f"Successfully installed plugin '{display_name}'.")


@hub.command("uninstall")
@click.argument("plugin_name", type=str, required=True)
@click.option(
    "--version",
    "-v",
    type=str,
    help="Version of the plugin to uninstall.",
)
def uninstall_plugin(plugin_name: str, version: Optional[str] = None) -> None:
    """Uninstall a plugin from the hub."""
    display_name = _plugin_display_name(plugin_name, version)

    # Get plugin from hub
    plugin = _get_plugin(plugin_name, version)
    if not plugin:
        error(f"Could not find plugin '{display_name}' on the hub.")

    # Check if plugin can be uninstalled
    wheel_name = plugin.wheel_name
    if not wheel_name:
        error(
            f"Plugin '{display_name}' is not available for " "uninstallation."
        )

    # pip uninstall the wheel
    logger.info(f"Uninstalling plugin '{display_name}'...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "uninstall", wheel_name, "-y"]
    )
    logger.info(f"Successfully uninstalled plugin '{display_name}'.")


@hub.command("pull")
@click.argument("plugin_name", type=str, required=True)
@click.option(
    "--version",
    "-v",
    type=str,
    help="Version of the plugin to pull.",
)
@click.option(
    "--output_dir",
    type=str,
    help="Output directory to pull the plugin to.",
)
def pull_plugin(
    plugin_name: str,
    version: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> None:
    """Pull a plugin from the hub."""
    display_name = _plugin_display_name(plugin_name, version)

    # Get plugin from hub
    plugin = _get_plugin(plugin_name, version)
    if not plugin:
        error(f"Could not find plugin '{display_name}' on the hub.")

    repo_url = plugin.repository_url
    subdir = plugin.repository_subdirectory

    # Clone the source repo
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), plugin_name)
    logger.info(f"Pulling plugin '{display_name}' to {output_dir}...")
    # If no subdir, we can clone directly into output_dir
    if not subdir:
        repo_path = plugin_dir = output_dir
    # Otherwise, we need to clone into a random dir and then move the subdir
    else:
        random_repo_name = f"_{uuid4()}"
        repo_path = os.path.abspath(
            os.path.join(os.getcwd(), random_repo_name)
        )
        plugin_dir = os.path.join(repo_path, subdir)

    # TODO: adjust below once all plugins have commit hashes
    # Clone the repo and checkout the right commit
    Repo.clone_from(
        url=repo_url,
        to_path=repo_path,
        # no_checkout=True,
    )
    # repo.git.checkout(commit)

    # Move the subdir into the output_dir
    if subdir:
        shutil.move(plugin_dir, output_dir)
        shutil.rmtree(repo_path)
    logger.info(f"Successfully pulled plugin '{display_name}'.")


@hub.command("push")
@click.option(
    "--plugin_name",
    "-n",
    type=str,
    help=(
        "Name of the plugin to push. If not provided, the name will be asked "
        "for interactively."
    ),
)
@click.option(
    "--version",
    "-v",
    type=str,
    help=(
        "Version of the plugin to push. Can only be set if the plugin already "
        "exists. If not provided, the version will be autoincremented."
    ),
)
@click.option(
    "--release_notes",
    "-r",
    type=str,
    help="Release notes for the plugin version.",
)
@click.option(
    "--repository_url",
    "-u",
    type=str,
    help="URL to the public Git repository containing the plugin source code.",
)
@click.option(
    "--repository_subdir",
    "-s",
    type=str,
    help="Subdirectory of the repository containing the plugin source code.",
)
@click.option(
    "--repository_branch",
    "-b",
    type=str,
    help="Branch to checkout from the repository.",
)
@click.option(
    "--repository_commit",
    "-c",
    type=str,
    help="Commit to checkout from the repository. Overrides --branch.",
)
@click.option(
    "tags",
    "--tag",
    "-t",
    type=str,
    multiple=True,
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Run the command in interactive mode.",
)
def push_plugin(
    plugin_name: Optional[str],
    version: Optional[str],
    release_notes: Optional[str],
    repository_url: Optional[str],
    repository_subdir: Optional[str],
    repository_branch: Optional[str],
    repository_commit: Optional[str],
    tags: List[str],
    interactive: bool,
) -> None:
    """Push a plugin to the hub."""
    # Validate that the plugin name is provided and available
    plugin_name, plugin_exists = _validate_plugin_name(
        plugin_name=plugin_name, interactive=interactive
    )

    # If the plugin exists, ask for version and release notes in interactive
    # mode.
    if plugin_exists and interactive:
        if not version:
            logger.info(
                "You are about to create a new version of plugin "
                f"'{plugin_name}'. By default, this will increment the minor "
                "version of the plugin. If you want to specify a different "
                "version, you can do so below. In that case, make sure that "
                "the version is of shape '<int>.<int>' and is higher than the "
                "current latest version of the plugin."
            )
            version = click.prompt("(Optional) plugin version")
        if not release_notes:
            logger.info(
                f"You are about to create a new version '{version}' of plugin "
                f"'{plugin_name}'. You can optionally provide release notes "
                "for this version below."
            )
            release_notes = click.prompt("(Optional) release notes")

    # Raise an error if the plugin does not exist and a version is provided.
    elif not plugin_exists and version:
        error(
            "You cannot specify a version for a plugin that does not exist "
            "yet. Please remove the '--version' flag and try again."
        )

    # Clone the repo and validate the commit / branch / subdir / structure
    repository_url, repo, repo_path = _clone_repository(
        repository_url, interactive=interactive
    )
    try:
        repository_commit = _validate_repository_commit(
            repository_commit=repository_commit,
            repo=repo,
            interactive=interactive,
        )
        if not repository_commit:
            repository_branch = _validate_repository_branch(
                repository_branch=repository_branch,
                repo=repo,
                interactive=interactive,
            )
        repository_subdir = _validate_repository_subdir(
            repository_subdir=repository_subdir,
            repo_path=repo_path,
            interactive=interactive,
        )
        if repository_subdir:
            plugin_path = os.path.join(repo_path, repository_subdir)
        else:
            plugin_path = repo_path
        _validate_repository_structure(plugin_path)
    finally:
        shutil.rmtree(repo_path)

    # In interactive mode, also ask for tags
    if interactive and not tags:
        tags = _ask_for_tags()

    # Make a create request to the hub
    plugin_request = PluginRequestModel(
        name=plugin_name,
        version=version,
        release_notes=release_notes,
        repository_url=repository_url,
        repository_subdirectory=repository_subdir,
        repository_branch=repository_branch,
        repository_commit=repository_commit,
        tags=",".join(tags),
    )
    plugin_response = _create_plugin(
        plugin_request=plugin_request,
        is_new_version=plugin_exists,
    )

    # Stream the build logs
    plugin_name = plugin_response.name
    plugin_version = plugin_response.version
    logger.info(
        "Thanks for submitting your plugin to the ZenML Hub. The plugin is now "
        "being built into an installable package. This may take a few minutes. "
        "To view the build logs, run "
        f"`zenml hub logs {plugin_name} --version {plugin_version}`."
    )
    # TODO
    # _stream_plugin_build_logs(
    #     plugin_name=plugin_response.name,
    #     plugin_version=plugin_response.version,
    # )


def _validate_plugin_name(
    plugin_name: Optional[str], interactive: bool
) -> Tuple[str, bool]:
    """Validate that the plugin name is provided and available.

    Args:
        plugin_name: The plugin name to validate.
        interactive: Whether to run in interactive mode.

    Returns:
        The validated plugin name, and whether the plugin already exists.
    """
    # Make sure the plugin name is provided.
    if not plugin_name:
        if not interactive:
            error("Plugin name not provided.")
        logger.info("Please enter a name for the plugin.")
        plugin_name = click.prompt("Plugin name")

    # Make sure the plugin name is available.
    while True:
        if plugin_name:
            existing_plugin = _get_plugin(plugin_name)
            plugin_exists = existing_plugin is not None
            # TODO: if plugin exists, check if it's the same user
            # if not existing_plugin or existing_plugin.user == user:
            return plugin_name, plugin_exists
        if not interactive:
            error("Plugin name not provided or not available.")
        logger.info(
            f"A plugin with name '{plugin_name}' already exists in the "
            "hub. Please choose a different name."
        )
        plugin_name = click.prompt("Plugin name")


def _clone_repository(
    repository_url: Optional[str], interactive: bool
) -> Tuple[str, Repo, str]:
    """Validate the provided URL and clone the repository from it.

    Args:
        repository_url: The URL to the repository to clone.
        interactive: Whether to run in interactive mode.

    Returns:
        - The validated URL to the repository,
        - The cloned repository,
        - The path to the cloned repository.
    """
    # Make sure the repository URL is provided.
    if not repository_url:
        if not interactive:
            error("Repository URL not provided.")
        logger.info(
            "Please enter the URL to the public Git repository containing "
            "the plugin source code."
        )
        repository_url = click.prompt("Repository URL")

    # Clone the repository from the URL.
    repo = None
    while not repo:
        repo_path = f"_{uuid4()}"
        try:
            assert repository_url is not None
            repo = Repo.clone_from(url=repository_url, to_path=repo_path)
        except Exception:
            if not interactive:
                raise
            logger.info(
                f"Could not clone repository from URL '{repository_url}'. "
                "Please enter a valid repository URL."
            )
            repository_url = click.prompt("Repository URL")

    return repository_url, repo, repo_path


def _validate_repository_commit(
    repository_commit: Optional[str], repo: Repo, interactive: bool
) -> Optional[str]:
    """Validate the provided repository commit.

    Args:
        repository_commit: The commit to validate.
        repo: The repository to validate the commit in.
        interactive: Whether to run in interactive mode.

    Returns:
        The validated commit.
    """
    # In interactive mode, ask for the commit if not provided
    if interactive and not repository_commit:
        confirmation = click.confirm(
            "Do you want to use the latest commit from the repository?"
        )
        if not confirmation:
            logger.info(
                "Please enter the commit to checkout from the repository."
            )
            repository_commit = click.prompt("Repository commit")

    # If a commit was provided, make sure it exists
    if repository_commit:
        commit_list = list(repo.iter_commits())
        while repository_commit not in commit_list:
            if not interactive:
                error("Commit does not exist.")
            logger.info(
                f"Commit '{repository_commit}' does not exist in the "
                f"repository. Please enter a valid commit hash."
            )
            repository_commit = click.prompt("Repository commit")

    return repository_commit


def _validate_repository_branch(
    repository_branch: Optional[str], repo: Repo, interactive: bool
) -> Optional[str]:
    """Validate the provided repository branch.

    Args:
        repository_branch: The branch to validate.
        repo: The repository to validate the branch in.
        interactive: Whether to run in interactive mode.

    Returns:
        The validated branch.
    """
    # In interactive mode, ask for the branch if not provided
    if interactive and not repository_branch:
        confirmation = click.confirm(
            "Do you want to use the 'main' branch of the repository?"
        )
        if not confirmation:
            logger.info(
                "Please enter the branch to checkout from the repository."
            )
            repository_branch = click.prompt("Repository branch")

    # If a branch and no commit was provided, make sure it exists
    if repository_branch:
        while repository_branch not in repo.heads:
            if not interactive:
                error("Branch does not exist.")
            logger.info(
                f"Branch '{repository_branch}' does not exist in the "
                f"repository. Please enter a valid branch name."
            )
            repository_branch = click.prompt("Repository branch")

    return repository_branch


def _validate_repository_subdir(
    repository_subdir: Optional[str], repo_path: str, interactive: bool
) -> Optional[str]:
    """Validate the provided repository subdirectory.

    Args:
        repository_subdir: The subdirectory to validate.
        repo_path: The path to the repository to validate the subdirectory in.
        interactive: Whether to run in interactive mode.

    Returns:
        The validated subdirectory.
    """
    # In interactive mode, ask for the subdirectory if not provided
    if interactive and not repository_subdir:
        confirmation = click.confirm(
            "Is the plugin source code in the root of the repository?"
        )
        if not confirmation:
            logger.info(
                "Please enter the subdirectory of the repository containing "
                "the plugin source code."
            )
            repository_subdir = click.prompt("Repository subdirectory")

    # If a subdir was provided, make sure it exists
    if repository_subdir:
        subdir_path = os.path.join(repo_path, repository_subdir)
        while not os.path.exists(subdir_path):
            if not interactive:
                error("Repository subdirectory does not exist.")
            logger.info(
                f"Subdirectory '{repository_subdir}' does not exist in the "
                f"repository. Please enter a valid subdirectory."
            )
            repository_subdir = click.prompt("Repository subdirectory")

    return repository_subdir


def _validate_repository_structure(plugin_root: str) -> None:
    """Validate the repository structure of a submitted ZenML Hub plugin.

    We expect the following structure:
    - README.md
    - requirements.txt
    - src/
        - zenml/
            - hub/
                - <one or more plugin directories>
                - (no `__init__.py`)
            - (no other files or directories)
        - (no other files or directories)

    Args:
        plugin_root: Root directory of the plugin.

    Raises:
        ValueError: If the repo does not have the correct structure.
    """
    # README.md exists.
    readme_path = os.path.join(plugin_root, "README.md")
    if not os.path.exists(readme_path):
        raise ValueError("README.md not found")

    # requirements.txt exists.
    requirements_path = os.path.join(plugin_root, "requirements.txt")
    if not os.path.exists(requirements_path):
        raise ValueError("requirements.txt not found")

    # src/ exists.
    src_path = os.path.join(plugin_root, "src")
    if not os.path.exists(src_path):
        raise ValueError("src/ not found")

    # src/ contains zenml/ and nothing else.
    src_contents = os.listdir(src_path)
    zenml_path = os.path.join(src_path, "zenml")
    if "zenml" not in src_contents or not os.path.isdir(zenml_path):
        raise ValueError("src/zenml/ not found")
    if len(src_contents) != 1:
        raise ValueError("src/ should only contain zenml/")

    # src/zenml/ contains hub/ and nothing else.
    zenml_contents = os.listdir(zenml_path)
    hub_path = os.path.join(zenml_path, "hub")
    if "hub" not in zenml_contents or not os.path.isdir(hub_path):
        raise ValueError("src/zenml/hub/ not found")
    if len(zenml_contents) != 1:
        raise ValueError("src/zenml/ should only contain hub/")

    # src/zenml/hub/ does not contain an `__init__.py` and is not empty.
    hub_contents = os.listdir(hub_path)
    if "__init__.py" in hub_contents:
        raise ValueError("src/zenml/hub/ may not contain a `__init__.py`")
    if len(hub_contents) == 0:
        raise ValueError("src/zenml/hub/ is empty")


def _ask_for_tags() -> List[str]:
    """Repeatedly ask the user for tags to assign to the plugin.

    Returns:
        A list of tags.
    """
    tags: List[str] = []
    while True:
        tag = click.prompt(
            "(Optional) enter tags you want to assign to the plugin.",
            default="",
        )
        if not tag:
            return tags
        tags.append(tag)


@hub.command("logs")
@click.argument("plugin_name", type=str, required=True)
@click.option(
    "--version",
    "-v",
    type=str,
    help="Version of the plugin to pull.",
)
def get_logs(plugin_name: str, version: Optional[str] = None) -> None:
    display_name = _plugin_display_name(plugin_name, version)

    # Get the plugin from the hub
    plugin = _get_plugin(plugin_name=plugin_name, plugin_version=version)
    if not plugin:
        error(f"Could not find plugin '{display_name}' on the hub.")

    # Stream the logs
    _stream_plugin_build_logs(
        plugin_name=plugin_name, plugin_version=plugin.version
    )
