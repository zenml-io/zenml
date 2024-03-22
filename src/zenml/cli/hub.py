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
import tempfile
from importlib.util import find_spec
from typing import Any, Dict, List, Optional, Tuple

import click

from zenml._hub.client import HubAPIError, HubClient
from zenml._hub.constants import (
    ZENML_HUB_ADMIN_USERNAME,
    ZENML_HUB_INTERNAL_TAG_PREFIX,
    ZENML_HUB_VERIFIED_TAG,
)
from zenml._hub.utils import parse_plugin_name, plugin_display_name
from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import declare, error, print_table, warning
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.models import (
    HubPluginRequestModel,
    HubPluginResponseModel,
    PluginStatus,
)

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.HUB)
def hub() -> None:
    """Interact with the ZenML Hub."""


@hub.command("list")
@click.option(
    "--all",
    "-a",
    is_flag=True,
    help="List all plugins, including those that are not available.",
)
@click.option(
    "--mine",
    "-m",
    is_flag=True,
    help="List only plugins that you own.",
)
@click.option(
    "--installed",
    "-i",
    is_flag=True,
    help="List only plugins that are installed.",
)
def list_plugins(
    all: bool = False, mine: bool = False, installed: bool = False
) -> None:
    """List all plugins available on the ZenML Hub.

    Args:
        all: Whether to list all plugins, including ones that are not available.
        mine: Whether to list only plugins that you own.
        installed: Whether to list only plugins that are installed.
    """
    client = HubClient()
    if mine and not client.auth_token:
        error(
            "You must be logged in to list your own plugins via --mine. "
            "Please run `zenml hub login` to login."
        )
    list_params: Dict[str, Any] = {"mine": mine}
    if not all:
        list_params["status"] = PluginStatus.AVAILABLE
    plugins = client.list_plugins(**list_params)
    if not plugins:
        declare("No plugins found.")
    if installed:
        plugins = [
            plugin
            for plugin in plugins
            if _is_plugin_installed(
                author=plugin.author, plugin_name=plugin.name
            )
        ]
    plugins_table = _format_plugins_table(plugins)
    print_table(plugins_table)


def _format_plugins_table(
    plugins: List[HubPluginResponseModel],
) -> List[Dict[str, str]]:
    """Helper function to format a list of plugins into a table.

    Args:
        plugins: The list of plugins.

    Returns:
        The formatted table.
    """
    plugins_table = []
    for plugin in sorted(plugins, key=_sort_plugin_key_fn):
        if _is_plugin_installed(author=plugin.author, plugin_name=plugin.name):
            installed_icon = ":white_check_mark:"
        else:
            installed_icon = ":x:"
        if plugin.status == PluginStatus.AVAILABLE:
            status_icon = ":white_check_mark:"
        elif plugin.status == PluginStatus.PENDING:
            status_icon = ":hourglass:"
        else:
            status_icon = ":x:"

        display_name = plugin_display_name(
            name=plugin.name,
            version=plugin.version,
            author=plugin.author,
        )
        display_data: Dict[str, str] = {
            "PLUGIN": display_name,
            "STATUS": status_icon,
            "INSTALLED": installed_icon,
            "MODULE": _get_plugin_module(
                author=plugin.author, plugin_name=plugin.name
            ),
            "PACKAGE NAME": plugin.package_name or "",
            "REPOSITORY URL": plugin.repository_url,
        }
        plugins_table.append(display_data)
    return plugins_table


def _sort_plugin_key_fn(
    plugin: HubPluginResponseModel,
) -> Tuple[str, str, str]:
    """Helper function to sort plugins by name, version and author.

    Args:
        plugin: The plugin to sort.

    Returns:
        A tuple of the plugin's author, name and version.
    """
    if plugin.author == ZENML_HUB_ADMIN_USERNAME:
        return "0", plugin.name, plugin.version  # Sort admin plugins first
    return plugin.author, plugin.name, plugin.version


@hub.command("install")
@click.argument("plugin_name", type=str, required=True)
@click.option(
    "--upgrade",
    "-u",
    is_flag=True,
    help="Upgrade the plugin if it is already installed.",
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
    upgrade: bool = False,
    no_deps: bool = False,
    yes: bool = False,
) -> None:
    """Install a plugin from the ZenML Hub.

    Args:
        plugin_name: Name of the plugin.
        upgrade: Whether to upgrade the plugin if it is already installed.
        no_deps: If set, dependencies of the plugin will not be installed.
        yes: If set, no confirmation will be asked for before installing.
    """
    with track_handler(
        event=AnalyticsEvent.ZENML_HUB_PLUGIN_INSTALL,
    ) as analytics_handler:
        client = HubClient()
        analytics_handler.metadata["hub_url"] = client.url
        author, plugin_name, plugin_version = parse_plugin_name(plugin_name)
        analytics_handler.metadata["plugin_name"] = plugin_name
        analytics_handler.metadata["plugin_author"] = author
        display_name = plugin_display_name(plugin_name, plugin_version, author)

        # Get plugin from hub
        plugin = client.get_plugin(
            name=plugin_name,
            version=plugin_version,
            author=author,
        )
        if not plugin:
            error(f"Could not find plugin '{display_name}' on the hub.")
        analytics_handler.metadata["plugin_version"] = plugin.version

        # Check if plugin can be installed
        index_url = plugin.index_url
        package_name = plugin.package_name
        if not index_url or not package_name:
            error(
                f"Plugin '{display_name}' is not available for installation."
            )

        # Check if plugin is already installed
        if (
            _is_plugin_installed(author=plugin.author, plugin_name=plugin.name)
            and not upgrade
        ):
            declare(f"Plugin '{plugin_name}' is already installed.")
            return

        # Show a warning if the plugin is not official or verified
        _is_zenml_plugin = plugin.author == ZENML_HUB_ADMIN_USERNAME
        _is_verified = plugin.tags and ZENML_HUB_VERIFIED_TAG in plugin.tags
        if not _is_zenml_plugin and not _is_verified:
            warning(
                f"Plugin '{display_name}' was not verified by ZenML and may "
                "contain arbitrary code. Please check the source code before "
                "installing to make sure it does what you expect."
            )

        # Install plugin requirements
        if plugin.requirements:
            requirements_str = " ".join(f"'{r}'" for r in plugin.requirements)
            install_requirements = False
            if not no_deps and not yes:
                install_requirements = click.confirm(
                    f"Plugin '{display_name}' requires the following "
                    f"packages to be installed: {requirements_str}. "
                    f"Do you want to install them now?"
                )
            if yes or install_requirements:
                declare(
                    f"Installing requirements for plugin '{display_name}': "
                    f"{requirements_str}..."
                )
                requirements_install_call = [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    *list(plugin.requirements),
                    "--upgrade",
                ]
                subprocess.check_call(requirements_install_call)
                declare(
                    f"Successfully installed requirements for plugin "
                    f"'{display_name}'."
                )
            else:
                warning(
                    f"Requirements for plugin '{display_name}' were not "
                    "installed. This might lead to errors in the future if the "
                    "requirements are not installed manually."
                )

        # pip install the wheel
        declare(
            f"Installing plugin '{display_name}' from "
            f"{index_url}{package_name}..."
        )
        plugin_install_call = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--index-url",
            index_url,
            package_name,
            "--no-deps",  # we already installed the requirements above
            "--upgrade",  # we already checked if the plugin is installed above
        ]
        subprocess.check_call(plugin_install_call)
        declare(f"Successfully installed plugin '{display_name}'.")


@hub.command("uninstall")
@click.argument("plugin_name", type=str, required=True)
def uninstall_plugin(plugin_name: str) -> None:
    """Uninstall a ZenML Hub plugin.

    Args:
        plugin_name: Name of the plugin.
    """
    with track_handler(
        event=AnalyticsEvent.ZENML_HUB_PLUGIN_UNINSTALL,
    ) as analytics_handler:
        client = HubClient()
        analytics_handler.metadata["hub_url"] = client.url
        author, plugin_name, plugin_version = parse_plugin_name(plugin_name)
        analytics_handler.metadata["plugin_name"] = plugin_name
        analytics_handler.metadata["plugin_author"] = author
        display_name = plugin_display_name(plugin_name, plugin_version, author)

        # Get plugin from hub
        plugin = client.get_plugin(
            name=plugin_name,
            version=plugin_version,
            author=author,
        )
        if not plugin:
            error(f"Could not find plugin '{display_name}' on the hub.")
        analytics_handler.metadata["plugin_version"] = plugin.version

        # Check if plugin can be uninstalled
        package_name = plugin.package_name
        if not package_name:
            error(
                f"Plugin '{display_name}' is not available for uninstallation."
            )

        # pip uninstall the wheel
        declare(f"Uninstalling plugin '{display_name}'...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "uninstall", package_name, "-y"]
        )
        declare(f"Successfully uninstalled plugin '{display_name}'.")


@hub.command("clone")
@click.argument("plugin_name", type=str, required=True)
@click.option(
    "--output_dir",
    "-o",
    type=str,
    help="Output directory to clone the plugin to.",
)
def clone_plugin(
    plugin_name: str,
    output_dir: Optional[str] = None,
) -> None:
    """Clone the source code of a ZenML Hub plugin.

    Args:
        plugin_name: Name of the plugin.
        output_dir: Output directory to clone the plugin to. If not specified,
            the plugin will be cloned to a directory with the same name as the
            plugin in the current working directory.
    """
    from zenml.utils.git_utils import clone_git_repository

    with track_handler(
        event=AnalyticsEvent.ZENML_HUB_PLUGIN_CLONE,
    ) as analytics_handler:
        client = HubClient()
        analytics_handler.metadata["hub_url"] = client.url
        author, plugin_name, plugin_version = parse_plugin_name(plugin_name)
        analytics_handler.metadata["plugin_name"] = plugin_name
        analytics_handler.metadata["plugin_author"] = author
        display_name = plugin_display_name(plugin_name, plugin_version, author)

        # Get plugin from hub
        plugin = client.get_plugin(
            name=plugin_name,
            version=plugin_version,
            author=author,
        )
        if not plugin:
            error(f"Could not find plugin '{display_name}' on the hub.")
        analytics_handler.metadata["plugin_version"] = plugin.version

        # Clone the source repo to a temp dir, then move the plugin subdir out
        repo_url = plugin.repository_url
        subdir = plugin.repository_subdirectory
        commit = plugin.repository_commit
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), plugin_name)
        declare(f"Cloning plugin '{display_name}' to {output_dir}...")
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                clone_git_repository(
                    url=repo_url, to_path=tmp_dir, commit=commit
                )
            except RuntimeError:
                error(
                    f"Could not find commit '{commit}' in repository "
                    f"'{repo_url}' of plugin '{display_name}'. This might "
                    "happen if the owner of the plugin has force-pushed to the "
                    "plugin repository or taken it down. Please report this "
                    "plugin version in the ZenML Hub or via Slack."
                )
            plugin_dir = os.path.join(tmp_dir, subdir or "")
            shutil.move(plugin_dir, output_dir)
        declare(f"Successfully Cloned plugin '{display_name}'.")


@hub.command("login")
@click.option(
    "--github",
    "-g",
    is_flag=True,
    help="Login via GitHub.",
)
@click.option(
    "--email",
    "-e",
    type=str,
    help="Login via ZenML Hub account using this email address.",
)
@click.option(
    "--password",
    "-p",
    type=str,
    help="Password of the ZenML Hub account.",
)
def login(
    github: bool = False,
    email: Optional[str] = None,
    password: Optional[str] = None,
) -> None:
    """Login to the ZenML Hub.

    Args:
        github: Login via GitHub.
        email: Login via ZenML Hub account using this email address.
        password: Password of the ZenML Hub account. Only used if `email` is
            specified.
    """
    if github:
        _login_via_github()
    elif email:
        if not password:
            password = click.prompt("Password", type=str, hide_input=True)
        _login_via_zenml_hub(email, password)
    else:
        declare(
            "You can either login via your ZenML Hub account or via GitHub."
        )
        confirmation = click.confirm("Login via ZenML Hub account?")
        if confirmation:
            _login_via_zenml_hub()
        else:
            _login_via_github()


def _login_via_zenml_hub(
    email: Optional[str] = None, password: Optional[str] = None
) -> None:
    """Login via ZenML Hub email and password.

    Args:
        email: Login via ZenML Hub account using this email address.
        password: Password of the ZenML Hub account. Only used if `email` is
            specified.
    """
    client = HubClient()
    if not email or not password:
        declare("Please enter your ZenML Hub credentials.")
    while not email:
        email = click.prompt("Email", type=str)
    while not password:
        password = click.prompt("Password", type=str, hide_input=True)
    try:
        client.login(email, password)
        me = client.get_me()
        if me:
            declare(f"Successfully logged in as: {me.username} ({me.email})!")
            return
        error("Could not retrieve user information from the ZenML Hub.")
    except HubAPIError as e:
        error(f"Could not login to the ZenML Hub: {e}")


def _login_via_github() -> None:
    """Login via GitHub."""
    client = HubClient()
    try:
        login_url = client.get_github_login_url()
    except HubAPIError as e:
        error(f"Could not retrieve GitHub login URL: {e}")
    declare(f"Please open the following URL in your browser: {login_url}")
    auth_token = click.prompt("Please enter your auth token", type=str)
    client.set_auth_token(auth_token)
    declare("Successfully logged in to the ZenML Hub.")


@hub.command("logout")
def logout() -> None:
    """Logout from the ZenML Hub."""
    client = HubClient()
    client.set_auth_token(None)
    declare("Successfully logged out from the ZenML Hub.")


@hub.command("submit")
@click.option(
    "--plugin_name",
    "-n",
    type=str,
    help=(
        "Name of the plugin to submit. If not provided, the name will be asked "
        "for interactively."
    ),
)
@click.option(
    "--version",
    "-v",
    type=str,
    help=(
        "Version of the plugin to submit. Can only be set if the plugin "
        "already exists. If not provided, the version will be auto-incremented."
    ),
)
@click.option(
    "--release_notes",
    "-r",
    type=str,
    help="Release notes for the plugin version.",
)
@click.option(
    "--description",
    "-d",
    type=str,
    help="Description of the plugin.",
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
def submit_plugin(
    plugin_name: Optional[str] = None,
    version: Optional[str] = None,
    release_notes: Optional[str] = None,
    description: Optional[str] = None,
    repository_url: Optional[str] = None,
    repository_subdir: Optional[str] = None,
    repository_branch: Optional[str] = None,
    repository_commit: Optional[str] = None,
    tags: Optional[List[str]] = None,
    interactive: bool = False,
) -> None:
    """Submit a plugin to the ZenML Hub.

    Args:
        plugin_name: Name of the plugin to submit. Needs to be set unless
            interactive mode is enabled.
        version: Version of the plugin to submit. Can only be set if the plugin
            already exists. If not provided, the version will be
            auto-incremented.
        release_notes: Release notes for the plugin version.
        description: Description of the plugin.
        repository_url: URL to the public Git repository containing the plugin
            source code. Needs to be set unless interactive mode is enabled.
        repository_subdir: Subdirectory of the repository containing the plugin
            source code.
        repository_branch: Branch to checkout from the repository.
        repository_commit: Commit to checkout from the repository. Overrides
            `repository_branch`.
        tags: Tags to add to the plugin.
        interactive: Whether to run the command in interactive mode, asking for
            missing or invalid parameters.
    """
    with track_handler(
        event=AnalyticsEvent.ZENML_HUB_PLUGIN_SUBMIT,
    ) as analytics_handler:
        client = HubClient()
        analytics_handler.metadata["hub_url"] = client.url

        # Validate that the user is logged in
        if not client.auth_token:
            error(
                "You must be logged in to contribute a plugin to the Hub. "
                "Please run `zenml hub login` to login."
            )
        me = client.get_me()
        if not me:
            error("Could not retrieve user information from the ZenML Hub.")
        if not me.username:
            error(
                "Your ZenML Hub account does not have a username yet. Please "
                "set a username in your account settings and try again."
            )
        username = me.username

        # Validate the plugin name and check if it exists
        plugin_name, plugin_exists = _validate_plugin_name(
            client=client,
            plugin_name=plugin_name,
            username=username,
            interactive=interactive,
        )

        # If the plugin exists, ask for version and release notes in
        # interactive mode.
        if plugin_exists and interactive:
            if not version:
                declare(
                    "You are about to create a new version of plugin "
                    f"'{plugin_name}'. By default, this will increment the "
                    "minor version of the plugin. If you want to specify a "
                    "different version, you can do so below. In that case, "
                    "make sure that the version is of shape '<int>.<int>' and "
                    "is higher than the current latest version of the plugin."
                )
                version = click.prompt("(Optional) plugin version", default="")
            if not release_notes:
                declare(
                    f"You are about to create a new version of plugin "
                    f"'{plugin_name}'. You can optionally provide release "
                    "notes for this version below."
                )
                release_notes = click.prompt(
                    "(Optional) release notes", default=""
                )

        # Clone the repo and validate the commit / branch / subdir / structure
        (
            repository_url,
            repository_commit,
            repository_branch,
            repository_subdir,
        ) = _validate_repository(
            url=repository_url,
            commit=repository_commit,
            branch=repository_branch,
            subdir=repository_subdir,
            interactive=interactive,
        )

        # In interactive mode, ask for a description if none is provided
        if interactive and not description:
            declare(
                "You can optionally provide a description for your plugin "
                "below. If not set, the first line of your README.md will "
                "be used."
            )
            description = click.prompt(
                "(Optional) plugin description", default=""
            )

        # Validate the tags
        if tags:
            tags = _validate_tags(tags=tags, interactive=interactive)
        else:
            tags = []

        # Make a create request to the hub
        plugin_request = HubPluginRequestModel(
            name=plugin_name,
            description=description,
            version=version,
            release_notes=release_notes,
            repository_url=repository_url,
            repository_subdirectory=repository_subdir,
            repository_branch=repository_branch,
            repository_commit=repository_commit,
            tags=tags,
        )
        plugin_response = client.create_plugin(
            plugin_request=plugin_request,
        )

        # Stream the build logs
        plugin_name = plugin_response.name
        plugin_version = plugin_response.version
        declare(
            "Thanks for submitting your plugin to the ZenML Hub. The plugin is "
            "now  being built into an installable package. This may take a few "
            "minutes. To view the build logs, run "
            f"`zenml hub logs {username}/{plugin_name}:{plugin_version}`."
        )


def _validate_plugin_name(
    client: HubClient,
    plugin_name: Optional[str],
    username: str,
    interactive: bool,
) -> Tuple[str, bool]:
    """Validate that the plugin name is provided and available.

    Args:
        client: The Hub client used to check if the plugin name is available.
        plugin_name: The plugin name to validate.
        username: The username of the current user.
        interactive: Whether to run in interactive mode.

    Returns:
        The validated plugin name, and whether the plugin already exists.
    """
    # Make sure the plugin name is provided.
    while not plugin_name:
        if not interactive:
            error("Plugin name not provided.")
        declare("Please enter a name for the plugin.")
        plugin_name = click.prompt("Plugin name")

    existing_plugin = client.get_plugin(name=plugin_name, author=username)
    return plugin_name, bool(existing_plugin)


def _validate_repository(
    url: Optional[str],
    commit: Optional[str],
    branch: Optional[str],
    subdir: Optional[str],
    interactive: bool,
) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Validate the provided repository arguments.

    Args:
        url: The URL to the repository to clone.
        commit: The commit to checkout.
        branch: The branch to checkout. Will be ignored if commit is provided.
        subdir: The subdirectory in which the plugin is located.
        interactive: Whether to run in interactive mode.

    Returns:
        The validated URL, commit, branch, and subdirectory.
    """
    from zenml.utils.git_utils import clone_git_repository

    while True:
        # Make sure the repository URL is provided.
        if not url:
            if not interactive:
                error("Repository URL not provided.")
            declare(
                "Please enter the URL to the public Git repository containing "
                "the plugin source code."
            )
            url = click.prompt("Repository URL")
        assert url is not None

        # In interactive mode, ask for the branch and commit if not provided
        if interactive and not branch and not commit:
            confirmation = click.confirm(
                "Do you want to use the latest commit from the 'main' branch "
                "of the repository?"
            )
            if not confirmation:
                confirmation = click.confirm(
                    "You can either use a specific commit or the latest commit "
                    "from one of your branches. Do you want to use a specific "
                    "commit?"
                )
                if confirmation:
                    declare("Please enter the SHA of the commit.")
                    commit = click.prompt("Repository commit")
                    branch = None
                else:
                    declare("Please enter the name of a branch.")
                    branch = click.prompt("Repository branch")
                    commit = None

        try:
            # Check if the URL/branch/commit are valid.
            with tempfile.TemporaryDirectory() as tmp_dir:
                clone_git_repository(
                    url=url,
                    commit=commit,
                    branch=branch,
                    to_path=tmp_dir,
                )

                # Check if the subdir exists and has the correct structure.
                subdir = _validate_repository_subdir(
                    repository_subdir=subdir,
                    repo_path=tmp_dir,
                    interactive=interactive,
                )

                return url, commit, branch, subdir

        except RuntimeError:
            repo_display_name = f"'{url}'"
            suggestion = "Please enter a valid repository URL"
            if commit:
                repo_display_name += f" (commit '{commit}')"
                suggestion += " and make sure the commit exists."
            elif branch:
                repo_display_name += f" (branch '{branch}')"
                suggestion += " and make sure the branch exists."
            else:
                suggestion += " and make sure the 'main' branch exists."
            msg = f"Could not clone repository from URL {repo_display_name}. "
            if not interactive:
                error(msg + suggestion)
            declare(msg + suggestion)
            url, branch, commit = None, None, None


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
    while True:
        # In interactive mode, ask for the subdirectory if not provided
        if interactive and not repository_subdir:
            confirmation = click.confirm(
                "Is the plugin source code in the root of the repository?"
            )
            if not confirmation:
                declare(
                    "Please enter the subdirectory of the repository "
                    "containing the plugin source code."
                )
                repository_subdir = click.prompt("Repository subdirectory")

        # If a subdir was provided, make sure it exists
        if repository_subdir:
            subdir_path = os.path.join(repo_path, repository_subdir)
            if not os.path.exists(subdir_path):
                if not interactive:
                    error("Repository subdirectory does not exist.")
                declare(
                    f"Subdirectory '{repository_subdir}' does not exist in the "
                    f"repository."
                )
                declare("Please enter a valid subdirectory.")
                repository_subdir = click.prompt(
                    "Repository subdirectory", default=""
                )
                continue

        # Check if the plugin structure is valid.
        if repository_subdir:
            plugin_path = os.path.join(repo_path, repository_subdir)
        else:
            plugin_path = repo_path
        try:
            _validate_repository_structure(plugin_path)
            return repository_subdir
        except ValueError as e:
            msg = (
                f"Plugin code structure at {repository_subdir} is invalid: "
                f"{str(e)}"
            )
            if not interactive:
                error(str(e))
            declare(msg)
            declare("Please enter a valid subdirectory.")
            repository_subdir = click.prompt("Repository subdirectory")


def _validate_repository_structure(plugin_root: str) -> None:
    """Validate the repository structure of a submitted ZenML Hub plugin.

    We expect the following structure:
    - src/__init__.py
    - README.md
    - requirements.txt
    - (Optional) logo.png

    Args:
        plugin_root: Root directory of the plugin.

    Raises:
        ValueError: If the repo does not have the correct structure.
    """
    # src/__init__.py exists.
    src_path = os.path.join(plugin_root, "src")
    if not os.path.exists(src_path):
        raise ValueError("src/ not found")
    init_path = os.path.join(src_path, "__init__.py")
    if not os.path.exists(init_path):
        raise ValueError("src/__init__.py not found")

    # README.md exists.
    readme_path = os.path.join(plugin_root, "README.md")
    if not os.path.exists(readme_path):
        raise ValueError("README.md not found")

    # requirements.txt exists.
    requirements_path = os.path.join(plugin_root, "requirements.txt")
    if not os.path.exists(requirements_path):
        raise ValueError("requirements.txt not found")


def _validate_tags(tags: List[str], interactive: bool) -> List[str]:
    """Validate the provided tags.

    Args:
        tags: The tags to validate.
        interactive: Whether to run in interactive mode.

    Returns:
        The validated tags.
    """
    if not tags:
        if not interactive:
            return []

        # In interactive mode, ask for tags if none were provided.
        return _ask_for_tags()

    # If tags were provided, print a warning if any of them is invalid.
    for tag in tags:
        if tag.startswith(ZENML_HUB_INTERNAL_TAG_PREFIX):
            warning(
                f"Tag '{tag}' will be ignored because it starts with "
                f"disallowed prefix '{ZENML_HUB_INTERNAL_TAG_PREFIX}'."
            )
    return tags


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
        if tag.startswith(ZENML_HUB_INTERNAL_TAG_PREFIX):
            warning(
                "User-defined tags may not start with "
                f"'{ZENML_HUB_INTERNAL_TAG_PREFIX}'."
            )
        else:
            tags.append(tag)


@hub.command("submit-batch")
@click.argument(
    "config", type=click.Path(exists=True, dir_okay=False), required=True
)
def batch_submit(config: str) -> None:
    """Batch submit plugins to the ZenML Hub.

    WARNING: This command is intended for advanced users only. It does not
    perform any client-side validation which might lead to server-side HTTP
    errors that are hard to debug if the config file you specify is invalid or
    contains invalid plugin definitions. When in doubt, use the
    `zenml hub submit` command instead.

    Args:
        config: Path to the config file. The config file is expected to be a
            list of plugin definitions. Each plugin definition must be a dict
            with keys and values matching the fields of `HubPluginRequestModel`:
            ```yaml
            - name: str
              version: str
              release_notes: str
              description: str
              repository_url: str
              repository_subdirectory: str
              repository_branch: str
              repository_commit: str
              logo_url: str
              tags:
                - str
                - ...
            - ...
            ```
    """
    from pydantic import ValidationError

    from zenml.utils.yaml_utils import read_yaml

    client = HubClient()
    config = read_yaml(config)
    if not isinstance(config, list):
        error("Config file must be a list of plugin definitions.")
    declare(f"Submitting {len(config)} plugins to the hub...")
    for plugin_dict in config:
        try:
            assert isinstance(plugin_dict, dict)
            plugin_request = HubPluginRequestModel(**plugin_dict)
            plugin = client.create_plugin(plugin_request=plugin_request)
        except (AssertionError, ValidationError, HubAPIError) as e:
            warning(f"Could not submit plugin: {str(e)}")
            continue
        display_name = plugin_display_name(
            name=plugin.name,
            version=plugin.version,
            author=plugin.author,
        )
        declare(f"Submitted plugin '{display_name}' to the hub.")


@hub.command("logs")
@click.argument("plugin_name", type=str, required=True)
def get_logs(plugin_name: str) -> None:
    """Get the build logs of a ZenML Hub plugin.

    Args:
        plugin_name: Name of the plugin.
    """
    client = HubClient()
    author, plugin_name, plugin_version = parse_plugin_name(plugin_name)
    display_name = plugin_display_name(plugin_name, plugin_version, author)

    # Get the plugin from the hub
    plugin = client.get_plugin(
        name=plugin_name,
        version=plugin_version,
        author=author,
    )
    if not plugin:
        error(f"Could not find plugin '{display_name}' on the hub.")

    if plugin.status == PluginStatus.PENDING:
        error(
            f"Plugin '{display_name}' is still being built. Please try "
            "again later."
        )

    if not plugin.build_logs:
        declare(
            f"Plugin '{display_name}' finished building, but no logs "
            "were found."
        )
        return

    for line in plugin.build_logs.splitlines():
        declare(line)


# GENERAL HELPER FUNCTIONS


def _is_plugin_installed(author: str, plugin_name: str) -> bool:
    """Helper function to check if a plugin is installed.

    Args:
        author: The author of the plugin.
        plugin_name: The name of the plugin.

    Returns:
        Whether the plugin is installed.
    """
    module_name = _get_plugin_module(author=author, plugin_name=plugin_name)
    try:
        spec = find_spec(module_name)
        return spec is not None
    except ModuleNotFoundError:
        return False


def _get_plugin_module(author: str, plugin_name: str) -> str:
    """Helper function to get the module name of a plugin.

    Args:
        author: The author of the plugin.
        plugin_name: The name of the plugin.

    Returns:
        The module name of the plugin.
    """
    module_name = "zenml.hub"
    if author != ZENML_HUB_ADMIN_USERNAME:
        module_name += f".{author}"
    module_name += f".{plugin_name}"
    return module_name
