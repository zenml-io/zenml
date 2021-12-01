#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from abc import abstractmethod
from typing import Any

import dash
import dash_cytoscape as cyto
from dash import dcc, html
from dash.dependencies import Input, Output

from zenml.enums import ExecutionStatus
from zenml.logger import get_logger
from zenml.post_execution.pipeline_run import PipelineRunView
from zenml.visualizers.base_pipeline_run_visualizer import (
    BasePipelineRunVisualizer,
)

logger = get_logger(__name__)


class PipelineRunLineageVisualizer(BasePipelineRunVisualizer):
    """Implementation of a lineage diagram via the [dash](
    https://plotly.com/dash/) and [dash-cyctoscape](
    https://dash.plotly.com/cytoscape) library."""

    ARTIFACT_PREFIX = "artifact_"
    STEP_PREFIX = "step_"
    STATUS_CLASS_MAPPING = {
        ExecutionStatus.CACHED: "blue",
        ExecutionStatus.FAILED: "red",
        ExecutionStatus.RUNNING: "yellow",
        ExecutionStatus.COMPLETED: "green",
    }

    @abstractmethod
    def visualize(
        self, object: PipelineRunView, *args: Any, **kwargs: Any
    ) -> dash.Dash:
        """Method to visualize pipeline runs via the Dash library. The layout
        puts every layer of the dag in a column.
        """

        app = dash.Dash(__name__)
        nodes = []
        edges = []
        start_x, start_y = 0, 0
        x, y = start_x, start_y
        for step in object.steps:
            step_output_artifacts = list(step.outputs.values())
            execution_id = (
                step_output_artifacts[0].producer_step.id
                if step_output_artifacts
                else step.id
            )
            nodes.append(
                {
                    "data": {
                        "id": self.STEP_PREFIX + str(step.id),
                        "execution_id": execution_id,
                        "label": f"{execution_id} / {step.name}",
                        "name": step.name,  # redundant for consistency
                        "type": "step",
                        "parameters": step.parameters,
                        "inputs": {k: v.uri for k, v in step.inputs.items()},
                        "outputs": {k: v.uri for k, v in step.outputs.items()},
                    },
                    "position": {
                        "x": x,
                        "y": y,
                    },
                    "classes": self.STATUS_CLASS_MAPPING[step.status],
                }
            )
            y += 1

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
                        "position": {
                            "x": x,
                            "y": y,
                        },
                        "classes": f"rectangle "
                        f"{self.STATUS_CLASS_MAPPING[step.status]}",
                    }
                )
                x += 1
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
                        "classes": f"edge-arrow "
                        f"{self.STATUS_CLASS_MAPPING[step.status]}"
                        + (" dashed" if artifact.is_cached else " solid"),
                    }
                )
            y += 1
            x = 0
        default_stylesheet = [
            # Group selectors
            {
                "selector": "node",
                "style": {
                    "content": "data(label)",
                },
            },
            {
                "selector": "edge",
                "style": {
                    "curve-style": "unbundled-bezier",
                },
            },
            # Class selectors
            {
                "selector": ".red",
                "style": {
                    "background-color": "#AD5D4E",
                    "line-color": "#AD5D4E",
                    "target-arrow-color": "#AD5D4E",
                },
            },
            {
                "selector": ".blue",
                "style": {
                    "background-color": "#22577A",
                    "line-color": "#22577A",
                    "target-arrow-color": "#22577A",
                },
            },
            {
                "selector": ".yellow",
                "style": {
                    "background-color": "#FFB100",
                    "line-color": "#FFB100",
                    "target-arrow-color": "#FFB100",
                },
            },
            {
                "selector": ".green",
                "style": {
                    "background-color": "#BFD7B5",
                    "line-color": "#BFD7B5",
                    "target-arrow-color": "#BFD7B5",
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

        app.layout = html.Div(
            [
                html.Button("Reset", id="bt-reset"),
                cyto.Cytoscape(
                    id="cytoscape",
                    layout={"name": "grid", "cols": y + 1},
                    # position=position,
                    elements=edges + nodes,
                    stylesheet=default_stylesheet,
                    style={"width": "100%", "height": "600px"},
                    zoom=1,
                ),
                dcc.Markdown(id="markdown-selected-node-data"),
            ]
        )

        @app.callback(
            Output("markdown-selected-node-data", "children"),
            Input("cytoscape", "selectedNodeData"),
        )
        def display_data(data_list):
            """Callback for the text area below the graph"""
            if data_list is None:
                return "Nothing Selected."

            text = ""
            for data in data_list:
                text += f'# {data["execution_id"]} / {data["name"]}' + "\n\n"
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
                    text += "## Inputs:" + "\n\n"
                    for k, v in data["inputs"].items():
                        text += f"**{k}** / {v}" + "\n\n"
                    text += "## Outputs:" + "\n\n"
                    for k, v in data["outputs"].items():
                        text += f"**{k}** / {v}" + "\n\n"
                    text += "## Params:"
                    for k, v in data["parameters"].items():
                        text += f"**{k}** / {v}" + "\n\n"
            return text

        @app.callback(
            [Output("cytoscape", "zoom"), Output("cytoscape", "elements")],
            [Input("bt-reset", "n_clicks")],
        )
        def reset_layout(n_clicks):
            """Resets the layout"""
            logger.debug(n_clicks, "clicked in reset button.")
            return [1, edges + nodes]

        app.run_server()
        return app
