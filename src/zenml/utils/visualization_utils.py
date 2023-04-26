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


def format_csv_visualization_as_html(csv_visualization: str) -> str:
    """Formats a CSV visualization as an HTML table.

    Args:
        csv_visualization: CSV visualization as a string.

    Returns:
        HTML table as a string.
    """
    table = "<table>"
    for row in csv_visualization.splitlines():
        table += "<tr>"
        for cell in row.split(","):
            table += f"<td>{cell}</td>"
        table += "</tr>"
    table += "</table>"
    return table
