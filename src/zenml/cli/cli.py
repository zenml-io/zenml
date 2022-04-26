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


from typing import Any, Dict, Optional, Sequence, Tuple, Union

import click
from click import Context, formatting
from click._compat import term_len

from zenml import __version__
from zenml.logger import set_root_verbosity


class GroupExt(click.Group):
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
        self.tag = tag if tag else "Other Commands"


class CustomFormatter(formatting.HelpFormatter):
    def __init__(
        self,
        indent_increment: int = 2,
        width: Optional[int] = None,
        max_width: Optional[int] = None,
    ) -> None:
        super(CustomFormatter, self).__init__(
            indent_increment, width, max_width
        )
        self.current_indent = 0

    def write_dl(
        self,
        rows: Sequence[Tuple[str, str]],
        col_max: int = 30,
        col_spacing: int = 2,
    ) -> None:
        """Writes a definition list into the buffer.  This is how options"""
        rows = list(sorted((rows), key=lambda x: x[0]))
        widths = formatting.measure_table(rows)

        if len(widths) == 2:
            first_col = min(widths[0], col_max) + col_spacing

            for first, second in formatting.iter_rows(rows, len(widths)):
                self.write(f"{'':>{self.current_indent}}{first}")
                if not second:
                    self.write("\n")
                    continue
                if term_len(first) <= first_col - col_spacing:
                    self.write(" " * (first_col - term_len(first)))
                else:
                    self.write("\n")
                    self.write(" " * (first_col + self.current_indent))

                text_width = max(self.width - first_col - 2, 10)
                wrapped_text = formatting.wrap_text(
                    second, text_width, preserve_paragraphs=True
                )
                lines = wrapped_text.splitlines()

                if lines:
                    self.write(f"{lines[0]}\n")

                    for line in lines[1:]:
                        self.write(
                            f"{'':>{first_col + self.current_indent}}{line}\n"
                        )
                else:
                    self.write("\n")
        elif len(widths) == 3:

            first_col = min(widths[0], col_max) + col_spacing
            second_col = min(widths[1], col_max) + col_spacing * 2

            current_tag = None
            for (first, second, third) in formatting.iter_rows(
                rows, len(widths)
            ):
                if current_tag != first:
                    current_tag = first
                    self.write("\n")
                    self.write(f"{'':>{self.current_indent}}{first}:\n")
                    continue

                if not third:
                    self.write("\n")
                    continue

                if term_len(first) <= first_col - col_spacing:
                    self.write(" " * self.current_indent * 2)
                else:
                    self.write("\n")
                    self.write(" " * (first_col + self.current_indent))

                self.write(f"{'':>{self.current_indent}}{second}")

                text_width = max(self.width - second_col - 4, 10)
                wrapped_text = formatting.wrap_text(
                    third, text_width, preserve_paragraphs=True
                )
                lines = wrapped_text.splitlines()

                if lines:
                    self.write(
                        " "
                        * (second_col - term_len(second) + self.current_indent)
                    )
                    self.write(f"{lines[0]}\n")

                    for line in lines[1:]:
                        self.write(
                            f"{'':>{second_col + self.current_indent * 4 }}{line}\n"
                        )
                else:
                    self.write("\n")
        else:
            raise TypeError("Expected three columns for definition list")


class ZenMLCLI(click.Group):
    """ """

    def get_help(self, ctx: Context) -> str:
        """Formats the help into a string and returns it.

        Calls :meth:`format_help` internally.
        """
        formatter = make_formatter()
        self.format_help(ctx, formatter)
        return formatter.getvalue().rstrip("\n")

    def format_commands(
        self, ctx: click.Context, formatter: formatting.HelpFormatter
    ) -> None:
        """Extra format methods for multi methods that adds all the commands
        after the options.
        """
        commands = []
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

        # allow for 3 times the default spacing
        if len(commands):
            rows = []
            for (tag, subcommand, cmd) in commands:
                help = cmd.get_short_help_str(limit=formatter.width)
                rows.append((tag, subcommand, help))

            if rows:
                with formatter.section("Available Commands By Tags for Zenml"):
                    formatter.write_dl(rows)

    # click.Group.format_commands = format_commands


def make_formatter() -> CustomFormatter:
    # breakpoint()
    return CustomFormatter()


@click.group(cls=ZenMLCLI)
@click.version_option(__version__, "--version", "-v")
def cli() -> None:
    """ZenML"""
    set_root_verbosity()


if __name__ == "__main__":
    cli()
