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

from typing import Optional

import click

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_decorator
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.config.global_config import GlobalConfiguration
from zenml.enums import CliCategories, LoggingLevels


# Analytics
@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def analytics() -> None:
    """Analytics for opt-in and opt-out."""


@analytics.command("get")
def is_analytics_opted_in() -> None:
    """Check whether user is opt-in or opt-out of analytics."""
    gc = GlobalConfiguration()
    cli_utils.declare(f"Analytics opt-in: {gc.analytics_opt_in}")


@analytics.command(
    "opt-in", context_settings=dict(ignore_unknown_options=True)
)
@track_decorator(AnalyticsEvent.OPT_IN_ANALYTICS)
def opt_in() -> None:
    """Opt-in to analytics."""
    gc = GlobalConfiguration()
    gc.analytics_opt_in = True
    cli_utils.declare("Opted in to analytics.")


@analytics.command(
    "opt-out", context_settings=dict(ignore_unknown_options=True)
)
@track_decorator(AnalyticsEvent.OPT_OUT_ANALYTICS)
def opt_out() -> None:
    """Opt-out of analytics."""
    gc = GlobalConfiguration()
    gc.analytics_opt_in = False
    cli_utils.declare("Opted out of analytics.")


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


# Config
@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def config() -> None:
    """Configuration management for ZenML."""


@config.command("set")
@click.argument("key", type=str)
@click.argument("value", type=str)
def set_config(key: str, value: str) -> None:
    """Set a configuration value.

    Args:
        key: Configuration key in the format 'section.key' (e.g., 'core.output')
        value: Configuration value to set

    Examples:
        zenml config set core.output json
        zenml config set core.output table
    """
    gc = GlobalConfiguration()

    # Parse key to handle nested configuration
    if key == "core.output":
        valid_formats = ["table", "json", "yaml", "tsv", "none"]
        if value not in valid_formats:
            cli_utils.error(
                f"Invalid output format '{value}'. Must be one of: {', '.join(valid_formats)}"
            )
            return
        gc.default_output = value
        cli_utils.declare(f"Set default output format to: {value}")
    else:
        cli_utils.error(f"Unknown configuration key: {key}")


@config.command("get")
@click.argument("key", type=str, required=False)
def get_config(key: Optional[str] = None) -> None:
    """Get configuration value(s).

    Args:
        key: Configuration key to get (optional). If not provided, shows all config.

    Examples:
        zenml config get core.output
        zenml config get
    """
    gc = GlobalConfiguration()

    if key is None:
        # Show all relevant configuration
        cli_utils.declare("Current configuration:")
        cli_utils.declare(f"  core.output: {gc.default_output}")
    elif key == "core.output":
        cli_utils.declare(f"Default output format: {gc.default_output}")
    else:
        cli_utils.error(f"Unknown configuration key: {key}")
