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

from typing import TYPE_CHECKING, Optional

from IPython.core.display import HTML, Image, JSON, Markdown, display

from zenml.artifacts.utils import load_artifact_visualization
from zenml.enums import VisualizationType
from zenml.environment import Environment

if TYPE_CHECKING:
    from zenml.models import ArtifactVersionResponse


def visualize_artifact(
    artifact: "ArtifactVersionResponse", title: Optional[str] = None
) -> None:
    """Visualize an artifact in notebook environments.

    Args:
        artifact: The artifact to visualize.
        title: Optional title to show before the visualizations.

    Raises:
        RuntimeError: If not in a notebook environment.
    """
    if not Environment.in_notebook():
        raise RuntimeError(
            "The `output.visualize()` method is only available in Jupyter "
            "notebooks. In all other runtime environments, please open "
            "your ZenML dashboard using `zenml up` and view the "
            "visualizations by clicking on the respective artifacts in the "
            "pipeline run DAG instead."
        )

    if not artifact.visualizations:
        return

    if title:
        display(Markdown(f"### {title}"))
    for i in range(len(artifact.visualizations)):
        visualization = load_artifact_visualization(artifact, index=i)
        if visualization.type == VisualizationType.IMAGE:
            display(Image(visualization.value))
        elif visualization.type == VisualizationType.HTML:
            display(HTML(visualization.value))
        elif visualization.type == VisualizationType.MARKDOWN:
            display(Markdown(visualization.value))
        elif visualization.type == VisualizationType.CSV:
            assert isinstance(visualization.value, str)
            table = format_csv_visualization_as_html(visualization.value)
            display(HTML(table))
        elif visualization.type == VisualizationType.JSON:
            display(JSON(visualization.value))
        else:
            display(visualization.value)


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
