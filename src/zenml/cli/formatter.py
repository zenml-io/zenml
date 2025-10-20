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

from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

from click import formatting

if TYPE_CHECKING:
    from typing import Callable

    term_len: Callable[[str], int]
else:
    try:
        from click.utils import term_len
    except Exception:
        from click._compat import term_len


def _safe_width(
    width: Optional[int], max_width: Optional[int], default: int = 80
) -> int:
    """Return a non-None width value suitable for wrapping.

    Click sets width to None in some non-interactive contexts. This helper
    ensures we always get a valid integer width, preferring the explicit width
    first, then max_width, then a sensible default.

    Args:
        width: Explicit terminal or content width to use when available.
        max_width: Upper bound to apply if width is not set or invalid.
        default: Fallback width used when neither width nor max_width is a
            positive integer.

    Returns:
        The effective positive integer width used for wrapping.
    """
    if isinstance(width, int) and width > 0:
        return width
    if isinstance(max_width, int) and max_width > 0:
        return max_width
    return default


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
        """Writes a definition list into the formatter buffer.

        Click 8.2 tightened validation so that definition list entries must be
        pairs.  Our CLI groups commands in tagged triples, so we detect that
        case and render it manually while delegating the standard behavior to
        Click for the classic two-column output.  This keeps the formatter
        compatible with both older Click releases (<8.2) and the newer ones
        without sacrificing the custom grouped layout.

        Args:
            rows: A sequence of tuples that represent the definition list
                entries.
            col_max: The maximum width of the first column.
            col_spacing: The number of spaces between columns.

        Raises:
            TypeError: If the provided rows do not represent two or three
                column entries.
        """
        normalized_rows: List[Tuple[str, ...]] = [tuple(row) for row in rows]

        if not normalized_rows:
            return

        unique_lengths = {len(row) for row in normalized_rows}

        if unique_lengths == {2}:
            two_col_rows = [(row[0], row[1]) for row in normalized_rows]
            super().write_dl(
                two_col_rows, col_max=col_max, col_spacing=col_spacing
            )
            return

        if unique_lengths == {3}:
            self._write_triple_definition_list(
                [(row[0], row[1], row[2]) for row in normalized_rows],
                col_max=col_max,
                col_spacing=col_spacing,
            )
            return

        raise TypeError(
            "Expected either two- or three-column definition list entries."
        )

    def _write_triple_definition_list(
        self,
        rows: List[Tuple[str, str, str]],
        col_max: int,
        col_spacing: int,
    ) -> None:
        widths = measure_table(rows)

        if len(widths) < 3:
            raise TypeError(
                "Expected three columns for tagged definition list entries."
            )

        # Compute target column offsets with spacing applied
        first_col = min(widths[0], col_max) + col_spacing
        second_col = min(widths[1], col_max) + col_spacing * 2

        current_tag: Optional[str] = None

        for first, second, third in iter_rows(rows, 3):
            # Print a category header when the tag changes
            if current_tag != first:
                current_tag = first
                self.write("\n")
                self.write(
                    f"[#431d93]{'':>{self.current_indent}}{first}:[/#431d93]\n"
                )

            # Preserve behavior for empty third-column values
            if not third:
                self.write("\n")
                continue

            # Layout for the command name column
            if term_len(first) <= first_col - col_spacing:
                self.write(" " * (self.current_indent * 2))
            else:
                self.write("\n")
                self.write(" " * (first_col + self.current_indent))

            # Command name with current indentation
            self.write(f"{'':>{self.current_indent}}{second}")

            # Wrap and render the description using a safe width calculation
            effective_width = _safe_width(
                self.width, getattr(self, "max_width", None)
            )
            text_width = max(effective_width - second_col - 4, 10)
            wrapped_text = formatting.wrap_text(
                third, text_width, preserve_paragraphs=True
            )
            lines = wrapped_text.splitlines()

            if lines:
                # First line appears on the same row as the command name
                self.write(
                    " " * (second_col - term_len(second) + self.current_indent)
                )
                self.write(f"{lines[0]}\n")

                # Continuation lines align with the description column
                for line in lines[1:]:
                    self.write(" " * (second_col + self.current_indent))
                    self.write(f"{line}\n")
            else:
                self.write("\n")
