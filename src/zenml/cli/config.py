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
from zenml.zen_stores.rest_zen_store import RestZenStoreConfiguration

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


# Global and repository configuration
@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def config() -> None:
    """Manage the global and local repository ZenML configuration."""


@config.command(
    "set",
    help=(
        """Change the global or repository configuration.

    Use this command to configure where ZenML stores its data (e.g. stacks,
    stack components, flavors etc.). You can choose between using the local
    filesystem by passing the `--local-store` flag, or a remote ZenML server
    by configuring the `--url`, `--username` and an optional `--project`.

    The configuration changes are applied to the global configuration by
    default. If you need to change the local configuration of a specific
    repository instead, you can pass the `--repo` flag while running the command
    from within the repository directory.

    Examples:

     - set the global configuration to use the local filesystem to store stacks,
     stack components and so on:

        zenml config set --local-store

     - set the global configuration to connect to a remote ZenML server:

        zenml config set --url=http://localhost:8080 --username=default --project=default

     - set the repository configuration to use the local filesystem to store
     stacks, stack components and so on in a database stored in the repository
     itself:

        zenml config set --local-store

     - set the repository configuration to connect to a remote ZenML
     server:

        zenml config set --repo --url=http://localhost:8080 --username=default --project=default

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
    "--local-store",
    is_flag=True,
    help="Configure ZenML to use the stacks stored on your local filesystem.",
)
@click.option(
    "--repo",
    is_flag=True,
    help="Configure the repository local settings instead of the global "
    "configuration settings.",
)
def config_set_command(
    url: Optional[str] = None,
    username: Optional[str] = None,
    local_store: bool = False,
    repo: bool = False,
) -> None:
    """Change the ZenML configuration.

    Args:
        url: The URL where the ZenML server is reachable.
        local_store: Configure ZenML to use the local store.
        username: The username that is used to authenticate with the ZenML
            server.
        repo: Configure the repository local settings instead of the global ones.
    """
    if repo and not Repository().root:
        cli_utils.error(
            "The `--repo` flag can only be used with an initialized "
            "repository. You need to run `zenml init` or change the "
            "current directory to an initialized repository root."
        )

    if local_store:
        if url or username:
            cli_utils.error(
                "The `url` and `--username` options can only be used"
                "to connect to a remote ZenML server. Hint: `--local-store` "
                "should probably not be set."
            )
        if repo:
            Repository().set_default_store()
        else:
            GlobalConfiguration().set_default_store()
    else:
        if url is None or username is None:
            cli_utils.error(
                "The `--url` and `--username` options are required to connect "
                "to a remote ZenML server. Alternatively, you can use the "
                "`--local-store` flag to configure ZenML to use the local "
                "filesystem."
            )
        store_config = RestZenStoreConfiguration(
            url=url,
            username=username,
        )
        if repo:
            Repository().set_store(store_config)
        else:
            GlobalConfiguration().set_store(store_config)


@config.command(
    "show",
    help="Show details about the active configuration.",
)
def config_show() -> None:
    """Show details about the active configuration."""
    gc = GlobalConfiguration()
    repo = Repository()

    repo_cfg = repo.store_config
    global_cfg = gc.store

    if repo.root:
        cli_utils.declare(f"Active repository root: {repo.root}")
    if repo_cfg is not None:
        cli_utils.declare(
            f"The repository store configuration is in effect "
            f"({repo._config_path()}):"
        )
        for key, value in repo_cfg.dict().items():
            cli_utils.declare(f" - {key}: {value}")
    elif global_cfg is not None:
        cli_utils.declare(
            f"The global store configuration is in effect "
            f"({gc._config_file()}):"
        )
        for key, value in global_cfg.dict().items():
            cli_utils.declare(f" - {key}: {value}")

    stack_scope = "repository" if repo.uses_local_active_stack else "global"
    cli_utils.declare(
        f"The active stack is: '{repo.active_stack_name}' ({stack_scope})"
    )
    project_scope = "repository" if repo.uses_local_active_project else "global"
    if not repo.active_project_name:
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
Components and Flavors. This can be configured globally as well as independently
for each ZenML repository that is initialized on a machine.

The default configuration is to store all this information on the local
filesystem:

```
$ zenml config show
Running without an active repository root.
The global store configuration is in effect (/home/stefan/.config/zenml/config.yaml):
 - type: sql
 - url: sqlite:////home/stefan/.config/zenml/zenml.db
The active stack is: 'default' (global)
The active project is not set.
```

The `zenml config set` CLI command can be used to change the global
configuration as well as the local configuration of a specific repository to
store the data on a remote ZenML server.

To change the global configuration to use a remote ZenML server, pass the URL
where the server can be reached along with the authentication credentials:

```
$ zenml config set --url=http://localhost:8080 --username=default
Updated the global store configuration.

$ zenml config show
Running without an active repository root.
The global store configuration is in effect (/home/stefan/.config/zenml/config.yaml):
 - type: rest
 - url: http://localhost:8080
 - username: default
 - password:
The active stack is: 'default' (global)
The active project is 'default' (global).
```

To switch the global configuration back to the default local store, pass the
`--local-store` flag:

```
$ zenml config set --local-store
Using the default store for the global config.

$ zenml config show
Running without an active repository root.
The global store configuration is in effect (/home/stefan/.config/zenml/config.yaml):
 - type: sql
 - url: sqlite:////home/stefan/.config/zenml/zenml.db
The active stack is: 'default' (global)
The active project is not set.
```

Newly initialized repositories don't have a store configuration yet, which
means that they will use the same stacks available in the global configuration.

```
/tmp/zenml$ zenml init
Initializing ZenML repository at /tmp/zenml.
ZenML repository initialized at /tmp/zenml.

/tmp/zenml$ zenml config show
Active repository root: /tmp/zenml
The global store configuration is in effect (/home/stefan/.config/zenml/config.yaml):
 - type: sql
 - url: sqlite:////home/stefan/.config/zenml/zenml.db
The active stack is: 'default' (repository)
The active project is not set.
```

The repository can be configured with storage settings independent from the
global configuration by passing the `--repo` flag to the `zenml config set`
command. Note that this only works when a repository is active.

The following configures a repository to store stacks, stack components etc.
in a database that is stored in the repository root directory. The stacks
and other objects stored in the repository will only be visible while the
repository is active:

```
tmp/zenml$ zenml config set --repo --local-store
Initializing database...
Registered stack with name 'default'.
Using the default store for the repository config.

/tmp/zenml$ zenml config show
Active repository root: /tmp/zenml
The repository store configuration is in effect (/tmp/zenml/.zen/config.yaml):
 - type: sql
 - url: sqlite:////tmp/zenml/.zen/zenml.db
The active stack is: 'default' (repository)
The active project is not set.
```
"""
            )
        )
