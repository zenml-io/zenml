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
"""Implementation of the pipeline run lineage visualizer."""

from typing import Any, Collection, Dict, List, Union

import dash
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import dcc, html
from dash.dependencies import Input, Output

from zenml.cli import utils as cli_utils
from zenml.enums import ExecutionStatus
from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.post_execution import PipelineRunView
from zenml.post_execution.lineage.lineage_graph import LineageGraph
from zenml.post_execution.lineage.node.artifact_node import ArtifactNode
from zenml.post_execution.lineage.node.step_node import StepNode
from zenml.visualizers import BaseVisualizer

logger = get_logger(__name__)

OVERALL_STYLE = {"fontFamily": "sans-serif"}
COLOR_RED = "#AD5D4E"
COLOR_BLUE = "#22577A"
COLOR_YELLOW = "#FFB100"
COLOR_GREEN = "#BFD7B5"

STYLESHEET = [
    # Group selectors
    {
        "selector": "node",
        "style": {
            "content": "data(label)",
            "width": "70%",
            "height": "70%",
            "font-size": "24px",
        },
    },
    {
        "selector": "edge",
        "style": {
            "curve-style": "bezier",
            "content": "data(label)",
        },
    },
    # Class selectors
    {
        "selector": ".red",
        "style": {
            "background-color": COLOR_RED,
            "line-color": COLOR_RED,
            "target-arrow-color": COLOR_RED,
        },
    },
    {
        "selector": ".blue",
        "style": {
            "background-color": COLOR_BLUE,
            "line-color": COLOR_BLUE,
            "target-arrow-color": COLOR_BLUE,
        },
    },
    {
        "selector": ".yellow",
        "style": {
            "background-color": COLOR_YELLOW,
            "line-color": COLOR_YELLOW,
            "target-arrow-color": COLOR_YELLOW,
        },
    },
    {
        "selector": ".green",
        "style": {
            "background-color": COLOR_GREEN,
            "line-color": COLOR_GREEN,
            "target-arrow-color": COLOR_GREEN,
        },
    },
    {"selector": ".rectangle", "style": {"shape": "rectangle"}},
    {
        "selector": ".edge-arrow",
        "style": {"target-arrow-shape": "triangle"},
    },
    {"selector": ".solid", "style": {"line-style": "solid"}},
    {"selector": ".dashed", "style": {"line-style": "dashed"}},
]


class PipelineRunLineageVisualizer(BaseVisualizer):
    """Implementation of a lineage diagram via the dash and dash-cytoscape libraries."""

    ARTIFACT_PREFIX = "artifact_"
    STEP_PREFIX = "step_"
    STATUS_CLASS_MAPPING = {
        ExecutionStatus.CACHED: "green",
        ExecutionStatus.FAILED: "red",
        ExecutionStatus.RUNNING: "yellow",
        ExecutionStatus.COMPLETED: "blue",
    }

    def visualize(
        self,
        object: PipelineRunView,
        magic: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> dash.Dash:
        """Method to visualize pipeline runs via the Dash library.

        The layout puts every layer of the dag in a column.

        Args:
            object: The pipeline run to visualize.
            magic: If True, the visualization is rendered in a magic mode.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            The Dash application.
        """
        # flake8: noqa: C901
        external_stylesheets = [
            dbc.themes.BOOTSTRAP,
            dbc.icons.BOOTSTRAP,
        ]
        if magic:
            if Environment.in_notebook():
                # Only import jupyter_dash in this case
                from jupyter_dash import JupyterDash  # noqa

                JupyterDash.infer_jupyter_proxy_config()

                app = JupyterDash(
                    __name__,
                    external_stylesheets=external_stylesheets,
                )
                mode = "inline"
            else:
                cli_utils.warning(
                    "Cannot set magic flag in non-notebook environments."
                )
        else:
            app = dash.Dash(
                __name__,
                external_stylesheets=external_stylesheets,
            )
            mode = None

        graph = LineageGraph()
        graph.generate_run_nodes_and_edges(object)
        first_step_id = graph.root_step_id

        # Parse lineage graph nodes
        nodes = []
        for node in graph.nodes:
            node_dict = node.dict()
            node_data = node_dict.pop("data")
            node_dict = {**node_dict, **node_data}
            node_dict["label"] = node_dict["name"]
            classes = self.STATUS_CLASS_MAPPING[node.data.status]
            if isinstance(node, ArtifactNode):
                classes = "rectangle " + classes
                node_dict["label"] += f" ({node_dict['artifact_data_type']})"
            dash_node = {"data": node_dict, "classes": classes}
            nodes.append(dash_node)

        # Parse lineage graph edges
        node_mapping = {node.id: node for node in graph.nodes}
        edges = []
        for edge in graph.edges:
            source_node = node_mapping[edge.source]
            if isinstance(source_node, StepNode):
                is_input_artifact = False
                step_node = node_mapping[edge.source]
                artifact_node = node_mapping[edge.target]
            else:
                is_input_artifact = True
                step_node = node_mapping[edge.target]
                artifact_node = node_mapping[edge.source]
            assert isinstance(artifact_node, ArtifactNode)
            artifact_is_cached = artifact_node.data.is_cached
            if is_input_artifact and artifact_is_cached:
                edge_status = self.STATUS_CLASS_MAPPING[ExecutionStatus.CACHED]
            else:
                edge_status = self.STATUS_CLASS_MAPPING[step_node.data.status]
            edge_style = "dashed" if artifact_node.data.is_cached else "solid"
            edges.append(
                {
                    "data": edge.dict(),
                    "classes": f"edge-arrow {edge_status} {edge_style}",
                }
            )

        app.layout = dbc.Row(
            [
                dbc.Container(f"Run: {object.name}", class_name="h2"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Row(
                                    [
                                        html.Span(
                                            [
                                                html.Span(
                                                    [
                                                        html.I(
                                                            className="bi bi-circle-fill me-1"
                                                        ),
                                                        "Step",
                                                    ],
                                                    className="me-2",
                                                ),
                                                html.Span(
                                                    [
                                                        html.I(
                                                            className="bi bi-square-fill me-1"
                                                        ),
                                                        "Artifact",
                                                    ],
                                                    className="me-4",
                                                ),
                                                dbc.Badge(
                                                    "Completed",
                                                    color=COLOR_BLUE,
                                                    className="me-1",
                                                ),
                                                dbc.Badge(
                                                    "Cached",
                                                    color=COLOR_GREEN,
                                                    className="me-1",
                                                ),
                                                dbc.Badge(
                                                    "Running",
                                                    color=COLOR_YELLOW,
                                                    className="me-1",
                                                ),
                                                dbc.Badge(
                                                    "Failed",
                                                    color=COLOR_RED,
                                                    className="me-1",
                                                ),
                                            ]
                                        ),
                                    ]
                                ),
                                dbc.Row(
                                    [
                                        cyto.Cytoscape(
                                            id="cytoscape",
                                            layout={
                                                "name": "breadthfirst",
                                                "roots": f'[id = "{first_step_id}"]',
                                            },
                                            elements=edges + nodes,
                                            stylesheet=STYLESHEET,
                                            style={
                                                "width": "100%",
                                                "height": "800px",
                                            },
                                            zoom=1,
                                        )
                                    ]
                                ),
                                dbc.Row(
                                    [
                                        dbc.Button(
                                            "Reset",
                                            id="bt-reset",
                                            color="primary",
                                            className="me-1",
                                        )
                                    ]
                                ),
                            ]
                        ),
                        dbc.Col(
                            [
                                dcc.Markdown(id="markdown-selected-node-data"),
                            ]
                        ),
                    ]
                ),
            ],
            className="p-5",
        )

        @app.callback(  # type: ignore[misc]
            Output("markdown-selected-node-data", "children"),
            Input("cytoscape", "selectedNodeData"),
        )
        def display_data(data_list: List[Dict[str, Any]]) -> str:
            """Callback for the text area below the graph.

            Args:
                data_list: The selected node data.

            Returns:
                str: The selected node data.
            """
            if data_list is None:
                return "Click on a node in the diagram."

            text = ""
            for data in data_list:
                if data["type"] == "artifact":
                    text += f"### Artifact '{data['name']}'" + "\n\n"
                    text += "#### Attributes:" + "\n\n"
                    for item in [
                        "execution_id",
                        "status",
                        "artifact_data_type",
                        "producer_step_id",
                        "parent_step_id",
                        "uri",
                    ]:
                        text += f"**{item}**: {data[item]}" + "\n\n"
                elif data["type"] == "step":
                    text += f"### Step '{data['name']}'" + "\n\n"
                    text += "#### Attributes:" + "\n\n"
                    for item in [
                        "execution_id",
                        "status",
                    ]:
                        text += f"**{item}**: {data[item]}" + "\n\n"
                    if data["inputs"]:
                        text += "#### Inputs:" + "\n\n"
                        for k, v in data["inputs"].items():
                            text += f"**{k}**: {v}" + "\n\n"
                    if data["outputs"]:
                        text += "#### Outputs:" + "\n\n"
                        for k, v in data["outputs"].items():
                            text += f"**{k}**: {v}" + "\n\n"
                    if data["parameters"]:
                        text += "#### Parameters:" + "\n\n"
                        for k, v in data["parameters"].items():
                            text += f"**{k}**: {v}" + "\n\n"
                    if data["configuration"]:
                        text += "#### Configuration:" + "\n\n"
                        for k, v in data["configuration"].items():
                            text += f"**{k}**: {v}" + "\n\n"
            return text

        @app.callback(  # type: ignore[misc]
            [Output("cytoscape", "zoom"), Output("cytoscape", "elements")],
            [Input("bt-reset", "n_clicks")],
        )
        def reset_layout(
            n_clicks: int,
        ) -> List[Union[int, List[Dict[str, Collection[str]]]]]:
            """Resets the layout.

            Args:
                n_clicks: The number of clicks on the reset button.

            Returns:
                The zoom and the elements.
            """
            logger.debug(n_clicks, "clicked in reset button.")
            return [1, edges + nodes]

        if mode is not None:
            app.run_server(mode=mode)
        app.run_server()
        return app
