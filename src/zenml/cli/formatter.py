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
"""Helper functions to format output for CLI."""

from typing import Dict, Iterable, Iterator, Optional, Sequence, Tuple

from click import formatting
from click._compat import term_len


def measure_table(rows: Iterable[Tuple[str, ...]]) -> Tuple[int, ...]:
    """Measure the width of each column in a table.

    Args:
        rows: The rows of the table.

    Returns:
        A tuple of the width of each column.
    """
    widths: Dict[int, int] = {}
    for row in rows:
        for idx, col in enumerate(row):
            widths[idx] = max(widths.get(idx, 0), term_len(col))

    return tuple(y for x, y in sorted(widths.items()))


def iter_rows(
    rows: Iterable[Tuple[str, ...]],
    col_count: int,
) -> Iterator[Tuple[str, ...]]:
    """Iterate over rows of a table.

    Args:
        rows: The rows of the table.
        col_count: The number of columns in the table.

    Yields:
        An iterator over the rows of the table.
    """
    for row in rows:
        yield row + ("",) * (col_count - len(row))


class ZenFormatter(formatting.HelpFormatter):
    """Override the default HelpFormatter to add a custom format for the help command output."""

    def __init__(
        self,
        indent_increment: int = 2,
        width: Optional[int] = None,
        max_width: Optional[int] = None,
    ) -> None:
        """Initialize the formatter.

        Args:
            indent_increment: The number of spaces to indent each level of
                nesting.
            width: The maximum width of the help output.
            max_width: The maximum width of the help output.
        """
        super(ZenFormatter, self).__init__(indent_increment, width, max_width)
        self.current_indent = 0

    def write_dl(
        self,
        rows: Sequence[Tuple[str, ...]],
        col_max: int = 30,
        col_spacing: int = 2,
    ) -> None:
        """Writes a definition list into the buffer.

        This is how options and commands are usually formatted.

        Arguments:
            rows: a list of items as tuples for the terms and values.
            col_max: the maximum width of the first column.
            col_spacing: the number of spaces between the first and
                            second column (and third).

        The default behavior is to format the rows in a definition list
        with rows of 2 columns following the format ``(term, value)``.
        But for new CLI commands, we want to format the rows in a definition
        list with rows of 3 columns following the format
        ``(term, value, description)``.

        Raises:
            TypeError: if the number of columns is not 2 or 3.
        """
        rows = list(rows)
        widths = measure_table(rows)

        if len(widths) == 2:
            first_col = min(widths[0], col_max) + col_spacing

            for first, second in iter_rows(rows, len(widths)):
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
            for first, second, third in iter_rows(rows, len(widths)):
                if current_tag != first:
                    current_tag = first
                    self.write("\n")
                    # Adding [#431d93] [/#431d93] makes the tag colorful when
                    # it is printed by rich print
                    self.write(
                        f"[#431d93]{'':>{self.current_indent}}{first}:[/#431d93]\n"
                    )

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
            raise TypeError(
                "Expected either three or two columns for definition list"
            )
