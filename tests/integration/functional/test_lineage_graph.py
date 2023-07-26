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
"""Tests for the lineage graph."""

from tests.integration.functional.zen_stores.utils import (
    constant_int_output_test_step,
    int_plus_one_test_step,
)
from zenml.lineage_graph.lineage_graph import (
    ARTIFACT_PREFIX,
    STEP_PREFIX,
    LineageGraph,
)
from zenml.metadata.metadata_types import MetadataTypeEnum, Uri


def test_generate_run_nodes_and_edges(
    clean_client, connected_two_step_pipeline
):
    """Tests that the created lineage graph has the right nodes and edges.

    We also write some mock metadata for both pipeline runs and steps runs here
    to test that they are correctly added to the lineage graph.
    """
    active_stack_model = clean_client.active_stack_model
    orchestrator_id = active_stack_model.components["orchestrator"][0].id

    # Create and retrieve a pipeline run
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    pipeline_instance.run()
    pipeline_run = clean_client.get_pipeline(
        "connected_two_step_pipeline"
    ).runs[0]

    # Write some metadata for the pipeline run
    clean_client.create_run_metadata(
        metadata={"orchestrator_url": Uri("https://www.ariaflow.org")},
        pipeline_run_id=pipeline_run.id,
        stack_component_id=orchestrator_id,
    )

    # Write some metadata for all steps
    steps = pipeline_run.steps
    for step_ in steps.values():
        clean_client.create_run_metadata(
            metadata={
                "experiment_tracker_url": Uri("https://www.aria_and_blupus.ai")
            },
            step_run_id=step_.id,
            stack_component_id=orchestrator_id,  # just link something
        )

        # Write some metadata for all artifacts
        for output_artifact in step_.outputs.values():
            clean_client.create_run_metadata(
                metadata={"aria_loves_alex": True},
                artifact_id=output_artifact.id,
            )

    # Get the run again so all the metadata is loaded
    pipeline_run = clean_client.get_pipeline(
        "connected_two_step_pipeline"
    ).runs[0]

    # Generate a lineage graph for the pipeline run
    graph = LineageGraph()
    graph.generate_run_nodes_and_edges(pipeline_run)

    # Check that the graph has the right attributes
    assert len(graph.nodes) == 4  # 2 steps + 2 artifacts
    assert (
        len(graph.edges) == 3
    )  # step_1 -> artifact_1 -> step_2 -> artifact_2
    assert graph.root_step_id == STEP_PREFIX + str(
        pipeline_run.steps["step_1"].id
    )

    # Check that the graph makes sense
    edge_id_to_model_mapping = {edge.id: edge for edge in graph.edges}
    node_id_to_model_mapping = {node.id: node for node in graph.nodes}
    for step_ in pipeline_run.steps.values():
        step_id = STEP_PREFIX + str(step_.id)

        # Check that each step has a corresponding node
        assert step_id in node_id_to_model_mapping

        # Check that each step node is connected to all of its output nodes
        for output_artifact in step_.outputs.values():
            artifact_id = ARTIFACT_PREFIX + str(output_artifact.id)
            assert artifact_id in node_id_to_model_mapping
            edge_id = step_id + "_" + artifact_id
            assert edge_id in edge_id_to_model_mapping
            edge = edge_id_to_model_mapping[edge_id]
            assert edge.source == step_id
            assert edge.target == artifact_id

        # Check that each step node is connected to all of its input nodes
        for input_artifact in step_.inputs.values():
            artifact_id = ARTIFACT_PREFIX + str(input_artifact.id)
            assert artifact_id in node_id_to_model_mapping
            edge_id = artifact_id + "_" + step_id
            assert edge_id in edge_id_to_model_mapping
            edge = edge_id_to_model_mapping[edge_id]
            assert edge.source == artifact_id
            assert edge.target == step_id

    # Check that the run, all steps, and all artifacts have metadata
    # Here we only check the last element in case we run this test with stack
    # components that add their own metadata in the future
    assert len(graph.run_metadata) > 0
    assert graph.run_metadata[-1] == (
        "orchestrator_url",
        "https://www.ariaflow.org",
        MetadataTypeEnum.URI,
    )
    for node in graph.nodes:
        node_metadata = node.data.metadata
        assert len(node_metadata) > 0
        if node.type == "step":
            assert node_metadata[-1] == (
                "experiment_tracker_url",
                "https://www.aria_and_blupus.ai",
                MetadataTypeEnum.URI,
            )
        elif node.type == "artifact":
            assert node_metadata[-1] == (
                "aria_loves_alex",
                "True",
                MetadataTypeEnum.BOOL,
            )
