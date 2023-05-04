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
"""Utility functions for dashboard visualizations."""


def format_csv_visualization_as_html(
    csv_visualization: str, max_rows: int = 10, max_cols: int = 10
) -> str:
    """Formats a CSV visualization as an HTML table.

    Args:
        csv_visualization: CSV visualization as a string.
        max_rows: Maximum number of rows to display. Remaining rows will be
            replaced by an ellipsis in the middle of the table.
        max_cols: Maximum number of columns to display. Remaining columns will
            be replaced by an ellipsis at the end of each row.

    Returns:
        HTML table as a string.
    """
    rows = csv_visualization.splitlines()
    html = ""

    # If there are fewer rows than the maximum, print all rows
    if len(rows) <= max_rows:
        for row in rows:
            html += _format_csv_row_as_html(row, max_cols=max_cols)

    else:
        # Else, replace middle rows with ellipsis
        half_max_rows = max_rows // 2

        # Print first half of rows
        for row in rows[:half_max_rows]:
            html += _format_csv_row_as_html(row, max_cols=max_cols)

        # Print ellipsis
        if len(rows) > max_rows:
            html += "<tr><td>...</td></tr>"

        # Print last half of rows
        for row in rows[-half_max_rows:]:
            html += _format_csv_row_as_html(row, max_cols=max_cols)

    return "<table>" + html + "</table>"


def _format_csv_row_as_html(row: str, max_cols: int = 10) -> str:
    """Formats a CSV row as an HTML table row.

    Args:
        row: CSV row as a string.
        max_cols: Maximum number of columns to display. Remaining columns will
            be replaced by an ellipsis at the end of the row.

    Returns:
        HTML table row as a string.
    """
    if not row:
        return ""

    csv_cols = row.split(",")
    html = ""
    for cell in csv_cols[:max_cols]:
        html += f"<td>{cell}</td>"
    if len(csv_cols) > max_cols:
        html += "<td>...</td>"
    return "<tr>" + html + "</tr>"
