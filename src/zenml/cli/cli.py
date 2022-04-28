from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import click
from click import Command, Context, formatting

from zenml import __version__
from zenml.cli.formatter import ZenFormatter
from zenml.enums import CliCategories
from zenml.logger import set_root_verbosity


class GroupExt(click.Group):
    """
    Override the default click Group to add a tag.
    The tag is used to group commands and groups of
    commands in the help output.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        tag: Optional[str] = None,
        commands: Optional[
            Union[Dict[str, click.Command], Sequence[click.Command]]
        ] = None,
        **kwargs: Dict[str, Any],
    ) -> None:
        super(GroupExt, self).__init__(name, commands, **kwargs)
        self.tag = tag if tag else CliCategories.OTHER_COMMANDS


class ZenContext(click.Context):
    formatter_class = ZenFormatter


class ZenMLCLI(click.Group):
    """
    Override the default click Group to create a custom
    format command help output.
    """

    context_class = ZenContext

    def get_help(self, ctx: Context) -> str:
        """Formats the help into a string and returns it.

        Calls :meth:`format_help` internally.
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)
        return formatter.getvalue().rstrip("\n")

    def format_commands(
        self, ctx: click.Context, formatter: formatting.HelpFormatter
    ) -> None:
        """
        Extra format methods for multi methods that adds all the commands
        after the options.
        This custom format commands is used to retrive the commands and
        groups of commands with a tag. In order to call the new custom format
        method, the command must be added to the ZenMLCLI class.
        """
        commands: List[Tuple[str, str, Union[Command, GroupExt]]] = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue
            if isinstance(cmd, GroupExt):
                commands.append((cmd.tag, subcommand, cmd))
            else:
                commands.append(("Other Commands", subcommand, cmd))

        if len(commands):
            rows = []
            for (tag, subcommand, cmd) in commands:
                help = cmd.get_short_help_str(limit=formatter.width)
                rows.append((tag, subcommand, help))

            if rows:
                with formatter.section(
                    "Available Commands By Group Category for Zenml"
                ):
                    formatter.write_dl(rows)  # type: ignore[arg-type]


@click.group(cls=ZenMLCLI)
@click.version_option(__version__, "--version", "-v")
def cli() -> None:
    """ZenML"""
    set_root_verbosity()


if __name__ == "__main__":
    cli()
