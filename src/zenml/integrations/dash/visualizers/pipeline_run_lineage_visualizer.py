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

from typing import Any, Collection, Dict, List, Union

import dash
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import dcc, html
from dash.dependencies import Input, Output

from zenml.enums import ExecutionStatus
from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.post_execution import PipelineRunView
from zenml.visualizers import BasePipelineRunVisualizer

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


class PipelineRunLineageVisualizer(BasePipelineRunVisualizer):
    """Implementation of a lineage diagram via the [dash](
    https://plotly.com/dash/) and [dash-cyctoscape](
    https://dash.plotly.com/cytoscape) library."""

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
        """Method to visualize pipeline runs via the Dash library. The layout
        puts every layer of the dag in a column.
        """
        external_stylesheets = [
            dbc.themes.BOOTSTRAP,
            dbc.icons.BOOTSTRAP,
        ]
        if magic:
            if Environment.in_notebook:
                # Only import jupyter_dash in this case
                from jupyter_dash import JupyterDash  # noqa

                JupyterDash.infer_jupyter_proxy_config()

                app = JupyterDash(
                    __name__,
                    external_stylesheets=external_stylesheets,
                )
                mode = "inline"
            else:
                # TODO [ENG-895]: Refactor this to raise a warning instead.
                raise AssertionError(
                    "Cannot set magic flag in non-notebook environments."
                )
        else:
            app = dash.Dash(
                __name__,
                external_stylesheets=external_stylesheets,
            )
            mode = None
        nodes, edges, first_step_id = [], [], None
        first_step_id = None
        for step in object.steps:
            step_output_artifacts = list(step.outputs.values())
            execution_id = (
                step_output_artifacts[0].producer_step.id
                if step_output_artifacts
                else step.id
            )
            step_id = self.STEP_PREFIX + str(step.id)
            if first_step_id is None:
                first_step_id = step_id
            nodes.append(
                {
                    "data": {
                        "id": step_id,
                        "execution_id": execution_id,
                        "label": f"{execution_id} / {step.entrypoint_name}",
                        "entrypoint_name": step.entrypoint_name,  # redundant for consistency
                        "name": step.name,  # redundant for consistency
                        "type": "step",
                        "parameters": step.parameters,
                        "inputs": {k: v.uri for k, v in step.inputs.items()},
                        "outputs": {k: v.uri for k, v in step.outputs.items()},
                    },
                    "classes": self.STATUS_CLASS_MAPPING[step.status],
                }
            )

            for artifact_name, artifact in step.outputs.items():
                nodes.append(
                    {
                        "data": {
                            "id": self.ARTIFACT_PREFIX + str(artifact.id),
                            "execution_id": artifact.id,
                            "label": f"{artifact.id} / {artifact_name} ("
                            f"{artifact.data_type})",
                            "type": "artifact",
                            "name": artifact_name,
                            "is_cached": artifact.is_cached,
                            "artifact_type": artifact.type,
                            "artifact_data_type": artifact.data_type,
                            "parent_step_id": artifact.parent_step_id,
                            "producer_step_id": artifact.producer_step.id,
                            "uri": artifact.uri,
                        },
                        "classes": f"rectangle "
                        f"{self.STATUS_CLASS_MAPPING[step.status]}",
                    }
                )
                edges.append(
                    {
                        "data": {
                            "source": self.STEP_PREFIX + str(step.id),
                            "target": self.ARTIFACT_PREFIX + str(artifact.id),
                        },
                        "classes": f"edge-arrow "
                        f"{self.STATUS_CLASS_MAPPING[step.status]}"
                        + (" dashed" if artifact.is_cached else " solid"),
                    }
                )

            for artifact_name, artifact in step.inputs.items():
                edges.append(
                    {
                        "data": {
                            "source": self.ARTIFACT_PREFIX + str(artifact.id),
                            "target": self.STEP_PREFIX + str(step.id),
                        },
                        "classes": "edge-arrow "
                        + (
                            f"{self.STATUS_CLASS_MAPPING[ExecutionStatus.CACHED]} dashed"
                            if artifact.is_cached
                            else f"{self.STATUS_CLASS_MAPPING[step.status]} solid"
                        ),
                    }
                )

        app.layout = dbc.Row(
            [
                dbc.Container(f"Run: {object.name}", class_name="h1"),
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
            """Callback for the text area below the graph"""
            if data_list is None:
                return "Click on a node in the diagram."

            text = ""
            for data in data_list:
                text += f'## {data["execution_id"]} / {data["name"]}' + "\n\n"
                if data["type"] == "artifact":
                    for item in [
                        "artifact_data_type",
                        "is_cached",
                        "producer_step_id",
                        "parent_step_id",
                        "uri",
                    ]:
                        text += f"**{item}**: {data[item]}" + "\n\n"
                elif data["type"] == "step":
                    text += "### Inputs:" + "\n\n"
                    for k, v in data["inputs"].items():
                        text += f"**{k}**: {v}" + "\n\n"
                    text += "### Outputs:" + "\n\n"
                    for k, v in data["outputs"].items():
                        text += f"**{k}**: {v}" + "\n\n"
                    text += "### Params:"
                    for k, v in data["parameters"].items():
                        text += f"**{k}**: {v}" + "\n\n"
            return text

        @app.callback(  # type: ignore[misc]
            [Output("cytoscape", "zoom"), Output("cytoscape", "elements")],
            [Input("bt-reset", "n_clicks")],
        )
        def reset_layout(
            n_clicks: int,
        ) -> List[Union[int, List[Dict[str, Collection[str]]]]]:
            """Resets the layout"""
            logger.debug(n_clicks, "clicked in reset button.")
            return [1, edges + nodes]

        if mode is not None:
            app.run_server(mode=mode)
        app.run_server()
        return app
