#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""CLI for manipulating ZenML local and global config file."""

from typing import TYPE_CHECKING, Optional

import click
from rich.markdown import Markdown

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.enums import CliCategories, LoggingLevels
from zenml.repository import Repository
from zenml.utils.analytics_utils import AnalyticsEvent, track_event

if TYPE_CHECKING:
    pass


# Analytics
@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def analytics() -> None:
    """Analytics for opt-in and opt-out."""


@analytics.command("get")
def is_analytics_opted_in() -> None:
    """Check whether user is opt-in or opt-out of analytics."""
    gc = GlobalConfiguration()
    cli_utils.declare(f"Analytics opt-in: {gc.analytics_opt_in}")


@analytics.command("opt-in", context_settings=dict(ignore_unknown_options=True))
def opt_in() -> None:
    """Opt-in to analytics."""
    gc = GlobalConfiguration()
    gc.analytics_opt_in = True
    cli_utils.declare("Opted in to analytics.")
    track_event(AnalyticsEvent.OPT_IN_ANALYTICS)


@analytics.command(
    "opt-out", context_settings=dict(ignore_unknown_options=True)
)
def opt_out() -> None:
    """Opt-out of analytics."""
    gc = GlobalConfiguration()
    gc.analytics_opt_in = False
    cli_utils.declare("Opted out of analytics.")
    track_event(AnalyticsEvent.OPT_OUT_ANALYTICS)


# Logging
@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def logging() -> None:
    """Configuration of logging for ZenML pipelines."""


# Setting logging
@logging.command("set-verbosity")
@click.argument(
    "verbosity",
    type=click.Choice(
        list(map(lambda x: x.name, LoggingLevels)), case_sensitive=False
    ),
)
def set_logging_verbosity(verbosity: str) -> None:
    """Set logging level.

    Args:
        verbosity: The logging level.

    Raises:
        KeyError: If the logging level is not supported.
    """
    verbosity = verbosity.upper()
    if verbosity not in LoggingLevels.__members__:
        raise KeyError(
            f"Verbosity must be one of {list(LoggingLevels.__members__.keys())}"
        )
    cli_utils.declare(f"Set verbosity to: {verbosity}")


# Global store configuration
@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def config() -> None:
    """Manage the global store ZenML configuration."""


@config.command(
    "set",
    help=(
        """Change the global store configuration.

    Use this command to configure where ZenML stores its data (e.g. stacks,
    stack components, flavors etc.). You can choose between using the local
    filesystem by passing the `--local-store` flag, or a remote ZenML server
    by configuring the `--url`, `--username`, `--password` and an optional
    `--project`.

    Examples:

     - set the global configuration to use the local filesystem to store stacks,
     stack components and so on:

        zenml config set --local-store

     - set the global configuration to connect to a remote ZenML server:

        zenml config set --url=http://localhost:8080 --username=default --project=default

    """
    ),
)
@click.option(
    "--url",
    "-u",
    help="The ZenML server URL to use for the configuration. This is required "
    "if you're connecting to a ZenML server.",
    required=False,
    type=str,
)
@click.option(
    "--username",
    help="The username that is used to authenticate with a ZenML server. This "
    "is required if you're connected to a ZenML server.",
    required=False,
    type=str,
)
@click.option(
    "--password",
    help="The password that is used to authenticate with a ZenML server. This "
    "is required if you're connected to a ZenML server. If omitted, a prompt "
    "will be shown to enter the password.",
    required=False,
    type=str,
)
@click.option(
    "--project",
    help="The username that is used to authenticate with a ZenML server. This "
    "is only required if you're connected to a ZenML server.",
    required=False,
    type=str,
)
@click.option(
    "--local-store",
    is_flag=True,
    help="Configure ZenML to use the stacks stored on your local filesystem.",
)
def config_set_command(
    url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    project: Optional[str] = None,
    local_store: bool = False,
) -> None:
    """Change the ZenML configuration.

    Args:
        url: The URL where the ZenML server is reachable.
        local_store: Configure ZenML to use the local store.
        username: The username that is used to authenticate with the ZenML
            server.
        password: The password that is used to authenticate with the ZenML
            server.
        project: The active project that is used to connect to the ZenML
            server.
    """
    from zenml.zen_stores.rest_zen_store import RestZenStoreConfiguration

    if local_store:
        if url or username or password or project:
            cli_utils.error(
                "The `--url`, `--username`, `--password` and `--project` "
                "options can only be used to connect to a remote ZenML server. "
                "Hint: `--local-store` should probably not be set."
            )
        GlobalConfiguration().set_default_store()
    else:
        if url is None or username is None:
            cli_utils.error(
                "The `--url` and `--username` options are required to connect "
                "to a remote ZenML server. Alternatively, you can use the "
                "`--local-store` flag to configure ZenML to use the local "
                "filesystem."
            )
        if password is None:
            password = click.prompt(
                f"Password for user {username}", hide_input=True, default=""
            )
        store_config = RestZenStoreConfiguration(
            url=url,
            username=username,
        )
        GlobalConfiguration().set_store(store_config)
        if project:
            try:
                Repository().set_active_project(project)
            except KeyError:
                cli_utils.error(
                    f"The project {project} does not exist on the server "
                    f"{url}. Please set another project by running `zenml "
                    f"project set`."
                )


@config.command(
    "describe",
    help="Show details about the active global configuration.",
)
def config_describe() -> None:
    """Show details about the active global configuration."""
    gc = GlobalConfiguration()
    repo = Repository()

    store_cfg = gc.store
    active_project_name = repo.active_project_name

    if repo.root:
        cli_utils.declare(f"Active repository root: {repo.root}")
    if store_cfg is not None:
        store_cfg_dict = store_cfg.dict()
        store_cfg_dict.pop("type")
        store_cfg_dict.pop("password", None)
        cli_utils.declare(f"The global configuration is ({gc._config_file()}):")
        for key, value in store_cfg_dict.items():
            cli_utils.declare(f" - {key}: '{value}'")

    stack_scope = "repository" if repo.uses_local_active_stack else "global"
    cli_utils.declare(
        f"The active stack is: '{repo.active_stack_model.name}' ({stack_scope})"
    )
    project_scope = "repository" if repo.uses_local_active_project else "global"
    if not active_project_name:
        cli_utils.declare("The active project is not set.")
    else:
        cli_utils.declare(
            f"The active project is: '{repo.active_project_name}' "
            f"({project_scope})"
        )


@config.command("explain")
def explain_config() -> None:
    """Explains the concept of ZenML configurations."""
    with console.pager():
        console.print(
            Markdown(
                """
The ZenML configuration that is managed through `zenml config` determines the
type of backend that ZenML uses to persist objects such as Stacks, Stack
Components and Flavors.

The default configuration is to store all this information on the local
filesystem:

```
$ zenml config describe
Running without an active repository root.
No active project is configured. Run zenml project set PROJECT_NAME to set the active project.
The global configuration is (/home/stefan/.config/zenml/config.yaml):
 - url: 'sqlite:////home/stefan/.config/zenml/zenml.db'
The active stack is: 'default' (global)
The active project is not set.
```

The `zenml config set` CLI command can be used to change the global
configuration as well as the local configuration of a specific repository to
store the data on a remote ZenML server.

To change the global configuration to use a remote ZenML server, pass the URL
where the server can be reached along with the authentication credentials:

```
$ zenml config set --url=http://localhost:8080 --username=default --project=default --password=
Updated the global store configuration.

$ zenml config describe
Running without an active repository root.
The global configuration is (/home/stefan/.config/zenml/config.yaml):
 - url: 'http://localhost:8080'
 - username: 'default'
The active stack is: 'default' (global)
The active project is: 'default' (global)
```

To switch the global configuration back to the default local store, pass the
`--local-store` flag:

```
$ zenml config set --local-store
Using the default store for the global config.

$ zenml config describe
Running without an active repository root.
The global configuration is (/home/stefan/.config/zenml/config.yaml):
 - url: 'sqlite:////home/stefan/.config/zenml/zenml.db'
The active stack is: 'default' (global)
The active project is: 'default' (global)
```
"""
            )
        )
