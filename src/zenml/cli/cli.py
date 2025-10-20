#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Core CLI functionality."""

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import click
import rich
from click import Command, Context, formatting

from zenml import __version__
from zenml.analytics import source_context
from zenml.cli.formatter import ZenFormatter
from zenml.client import Client
from zenml.enums import CliCategories, SourceContextTypes
from zenml.logger import set_root_verbosity
from zenml.utils import source_utils


class TagGroup(click.Group):
    """Override the default click Group to add a tag.

    The tag is used to group commands and groups of
    commands in the help output.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        tag: Optional[CliCategories] = None,
        commands: Optional[
            Union[Dict[str, click.Command], Sequence[click.Command]]
        ] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Tag group.

        Args:
            name: The name of the group.
            tag: The tag of the group.
            commands: The commands of the group.
            kwargs: Additional keyword arguments.
        """
        super(TagGroup, self).__init__(name, commands, **kwargs)
        self.tag = tag or CliCategories.OTHER_COMMANDS


class ZenContext(click.Context):
    """Override the default click Context to add the new Formatter."""

    formatter_class = ZenFormatter


class ZenMLCLI(click.Group):
    """Custom click Group to create a custom format command help output."""

    context_class = ZenContext

    def get_help(self, ctx: Context) -> str:
        """Formats the help into a string and returns it.

        Calls :meth:`format_help` internally.

        Args:
            ctx: The click context.

        Returns:
            The formatted help string.
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)
        # TODO [ENG-862]: Find solution for support console.pager and color
        #   support in print
        rich.print(formatter.getvalue().rstrip("\n"))
        return ""

    def format_commands(
        self, ctx: click.Context, formatter: formatting.HelpFormatter
    ) -> None:
        """Multi methods that adds all the commands after the options.

        This custom format_commands method is used to retrieve the commands and
        groups of commands with a tag. In order to call the new custom format
        method, the command must be added to the ZenML CLI class.

        Args:
            ctx: The click context.
            formatter: The click formatter.
        """
        commands: List[
            Tuple[CliCategories, str, Union[Command, TagGroup]]
        ] = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None or cmd.hidden:
                continue
            category = (
                cmd.tag
                if isinstance(cmd, TagGroup)
                else CliCategories.OTHER_COMMANDS
            )
            commands.append(
                (
                    category,
                    subcommand,
                    cmd,
                )
            )

        if len(commands):
            ordered_categories = list(CliCategories.__members__.values())
            commands = list(
                sorted(
                    commands,
                    key=lambda x: (
                        ordered_categories.index(x[0]),
                        x[0].value,
                        x[1],
                    ),
                )
            )
            rows: List[Tuple[str, str, str]] = []
            for tag, subcommand, cmd in commands:
                help_ = cmd.get_short_help_str(limit=formatter.width)
                rows.append((tag.value, subcommand, help_))
            if rows:
                if isinstance(formatter, ZenFormatter):
                    section_title = "[dim cyan]Available ZenML Commands (grouped)[/dim cyan]"
                    with formatter.section(section_title):
                        formatter.write_dl(rows)  # type: ignore[arg-type]
                else:
                    # Fallback: use simple pairs without category and avoid rich markup in header
                    section_title = "Available ZenML Commands"
                    with formatter.section(section_title):
                        pair_rows: List[Tuple[str, str]] = [
                            (subcmd, help_) for _, subcmd, help_ in rows
                        ]
                        formatter.write_dl(pair_rows)


@click.group(cls=ZenMLCLI, invoke_without_command=True)
@click.version_option(__version__, "--version", "-v")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """CLI base command for ZenML."""
    set_root_verbosity()
    source_context.set(SourceContextTypes.CLI)
    repo_root = Client.find_repository()
    if not repo_root:
        # If we're not inside a ZenML repository, use the current working
        # directory as the source root, as otherwise the __main__ module used
        # as a source root is the CLI script located in the python site
        # packages directory
        source_utils.set_custom_source_root(source_root=os.getcwd())

    # Manually show help and exit with code 0 when invoked without a subcommand.
    # Click 8.2+ raises NoArgsIsHelpError before the callback runs when
    # no_args_is_help=True. By relying solely on invoke_without_command=True
    # and handling help here, we ensure consistent behavior across Click
    # versions while leveraging our custom help formatter in ZenMLCLI.get_help().
    if ctx.invoked_subcommand is None and not ctx.resilient_parsing:
        ctx.command.get_help(ctx)
        ctx.exit(0)


if __name__ == "__main__":
    cli()
