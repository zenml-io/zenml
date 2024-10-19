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

from typing import TYPE_CHECKING
from uuid import UUID

from typing_extensions import Annotated

from tests.integration.functional.zen_stores.utils import (
    constant_int_output_test_step,
    int_plus_one_test_step,
)
from zenml import load_artifact, pipeline, save_artifact, step
from zenml.artifacts.external_artifact import ExternalArtifact
from zenml.enums import MetadataResourceTypes
from zenml.lineage_graph.lineage_graph import (
    ARTIFACT_PREFIX,
    STEP_PREFIX,
    LineageGraph,
)
from zenml.metadata.metadata_types import MetadataTypeEnum, Uri
from zenml.models import PipelineRunResponse

if TYPE_CHECKING:
    from zenml.client import Client


def test_generate_run_nodes_and_edges(
    clean_client: "Client", connected_two_step_pipeline
):
    """Tests that the created lineage graph has the right nodes and edges.

    We also write some mock metadata for both pipeline runs and steps runs here
    to test that they are correctly added to the lineage graph.
    """
    active_stack_model = clean_client.active_stack_model
    orchestrator_id = active_stack_model.components["orchestrator"][0].id

    # Create and retrieve a pipeline run
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step,
        step_2=int_plus_one_test_step,
    )
    pipeline_instance()
    pipeline_run = clean_client.get_pipeline(
        "connected_two_step_pipeline"
    ).runs[0]

    # Write some metadata for the pipeline run
    clean_client.create_run_metadata(
        metadata={"orchestrator_url": Uri("https://www.ariaflow.org")},
        resource_id=pipeline_run.id,
        resource_type=MetadataResourceTypes.PIPELINE_RUN,
        stack_component_id=orchestrator_id,
    )

    # Write some metadata for all steps
    steps = pipeline_run.steps
    for step_ in steps.values():
        clean_client.create_run_metadata(
            metadata={
                "experiment_tracker_url": Uri("https://www.aria_and_blupus.ai")
            },
            resource_id=step_.id,
            resource_type=MetadataResourceTypes.STEP_RUN,
            stack_component_id=orchestrator_id,  # just link something
        )

        # Write some metadata for all artifacts
        for output_artifact in step_.outputs.values():
            clean_client.create_run_metadata(
                metadata={"aria_loves_alex": True},
                resource_id=output_artifact.id,
                resource_type=MetadataResourceTypes.ARTIFACT_VERSION,
            )

    # Get the run again so all the metadata is loaded
    pipeline_run = clean_client.get_pipeline(
        "connected_two_step_pipeline"
    ).runs[0]

    # Generate a lineage graph for the pipeline run
    graph = LineageGraph()
    graph.generate_run_nodes_and_edges(pipeline_run)

    # Check that the graph has the right attributes
    # 2 steps + 2 artifacts
    assert len(graph.nodes) == 4
    # 3 edges: step_1 -> artifact_1 -> step_2 -> artifact_2
    assert len(graph.edges) == 3

    # Check that the graph makes sense
    _validate_graph(graph, pipeline_run)

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


@step
def int_step(a: int = 1) -> int:
    return a


@step
def str_step(b: str = "a") -> str:
    return b


@pipeline
def pipeline_with_direct_edge():
    int_step()
    str_step(after=["int_step"])


def test_add_direct_edges(clean_client: "Client"):
    """Test that direct `.after(...)` edges are added to the lineage graph."""

    # Create and retrieve a pipeline run
    pipeline_with_direct_edge()
    run_ = pipeline_with_direct_edge.model.last_run

    # Generate a lineage graph for the pipeline run
    graph = LineageGraph()
    graph.generate_run_nodes_and_edges(run_)

    # Check that the graph has the right attributes
    # 2 steps + 2 artifacts
    assert len(graph.nodes) == 4
    # 3 edges: int_step -> a; int_step -> str_step; str_step -> b
    assert len(graph.edges) == 3

    # Check that the graph generally makes sense
    _validate_graph(graph, run_)

    # Check that the direct edge is added
    node_ids = [node.id for node in graph.nodes]
    direct_edge_exists = False
    for edge in graph.edges:
        if edge.source in node_ids and edge.target in node_ids:
            direct_edge_exists = True
    assert direct_edge_exists


@pipeline
def first_pipeline():
    int_step()


@step
def external_artifact_loader_step(a: int) -> int:
    c = a
    return c


@pipeline
def second_pipeline(artifact_version_id: UUID):
    external_artifact_loader_step(a=ExternalArtifact(value=1))


def test_add_external_artifacts(clean_client: "Client"):
    """Test that external artifacts are added to the lineage graph."""

    # Create and retrieve a pipeline run
    first_pipeline()
    second_pipeline(first_pipeline.model.last_run.steps["int_step"].output.id)
    run_ = second_pipeline.model.last_run

    # Generate a lineage graph for the pipeline run
    graph = LineageGraph()
    graph.generate_run_nodes_and_edges(run_)

    # Check that the graph has the right attributes
    # 1 step, 1 artifact, 1 external artifact
    assert len(graph.nodes) == 3
    # 2 edges: a -> external_artifact_loader_step -> c
    assert len(graph.edges) == 2

    # Check that the graph generally makes sense
    _validate_graph(graph, run_)

    # Check that the external artifact is a node in the graph
    artifact_version_ids_of_run = {
        artifact_version.id for artifact_version in run_.artifact_versions
    }
    external_artifact_node_id = None
    for node in graph.nodes:
        if node.type == "artifact":
            if node.data.execution_id not in artifact_version_ids_of_run:
                external_artifact_node_id = node.id
    assert external_artifact_node_id

    # Check that the external artifact is connected to the step
    step_nodes = [node for node in graph.nodes if node.type == "step"]
    assert len(step_nodes) == 1
    step_node = step_nodes[0]
    external_artifact_is_input_of_step = False
    for edge in graph.edges:
        if (
            edge.source == external_artifact_node_id
            and edge.target == step_node.id
        ):
            external_artifact_is_input_of_step = True
    assert external_artifact_is_input_of_step


@step
def manual_artifact_saving_step() -> Annotated[int, "output"]:
    """A step that logs an artifact."""
    save_artifact(1, name="saved_unconsumed")
    save_artifact(2, name="saved_consumed")
    return 3


@step
def manual_artifact_loading_step(input: int) -> None:
    """A step that loads an artifact."""
    load_artifact("saved_consumed")
    load_artifact("saved_before")


@pipeline
def saving_loading_pipeline():
    output = manual_artifact_saving_step()
    manual_artifact_loading_step(input=output)


def test_manual_save_load_artifact(clean_client):
    """Test that manually saved and loaded artifacts are added to the graph."""

    # Save an artifact before the pipeline run
    save_artifact(4, name="saved_before")

    # Create and retrieve a pipeline run
    saving_loading_pipeline()
    run_ = saving_loading_pipeline.model.last_run

    # Generate a lineage graph for the pipeline run
    graph = LineageGraph()
    graph.generate_run_nodes_and_edges(run_)

    # Check that the graph has the right attributes
    # 6 = 2 steps + 4 artifacts (3 from save step, 1 additional from load step)
    assert len(graph.nodes) == 6
    # 12 edges (3 per step)
    assert len(graph.edges) == 6

    # Check that the graph generally makes sense
    _validate_graph(graph, run_)

    # Check that "saved_unconsumed", "saved_consumed", and "saved_before" are
    # nodes in the graph
    saved_unconsumed_node_id = None
    saved_consumed_node_id = None
    saved_before_node_id = None
    for node in graph.nodes:
        if node.type == "artifact":
            if node.data.name == "saved_unconsumed":
                saved_unconsumed_node_id = node.id
            elif node.data.name == "saved_consumed":
                saved_consumed_node_id = node.id
            elif node.data.name == "saved_before":
                saved_before_node_id = node.id
    assert saved_unconsumed_node_id
    assert saved_consumed_node_id
    assert saved_before_node_id

    # Check that "saved_unconsumed" and "saved_consumed" are outputs of step 1
    step_nodes = [node for node in graph.nodes if node.type == "step"]
    saved_unconsumed_is_output = False
    saved_consumed_is_output = False
    for edge in graph.edges:
        if edge.source == step_nodes[0].id:
            if edge.target == saved_unconsumed_node_id:
                saved_unconsumed_is_output = True
            elif edge.target == saved_consumed_node_id:
                saved_consumed_is_output = True
    assert saved_unconsumed_is_output
    assert saved_consumed_is_output

    # Check that "saved_consumed" and "saved_before" are inputs of step 2
    saved_consumed_is_input = False
    saved_before_is_input = False
    for edge in graph.edges:
        if edge.target == step_nodes[1].id:
            if edge.source == saved_consumed_node_id:
                saved_consumed_is_input = True
            elif edge.source == saved_before_node_id:
                saved_before_is_input = True
    assert saved_consumed_is_input
    assert saved_before_is_input


def _validate_graph(
    graph: LineageGraph, pipeline_run: PipelineRunResponse
) -> None:
    """Validates that the generated lineage graph matches the pipeline run.

    Args:
        graph: The generated lineage graph.
        pipeline_run: The pipeline run used to generate the lineage graph.
    """
    edge_id_to_model_mapping = {edge.id: edge for edge in graph.edges}
    node_id_to_model_mapping = {node.id: node for node in graph.nodes}
    for step_ in pipeline_run.steps.values():
        step_id = STEP_PREFIX + str(step_.id)

        # Check that each step has a corresponding node
        assert step_id in node_id_to_model_mapping

        # Check that each step node is connected to all of its output nodes
        for output_artifact in step_.outputs.values():
            artifact_version_id = ARTIFACT_PREFIX + str(output_artifact.id)
            assert artifact_version_id in node_id_to_model_mapping
            edge_id = step_id + "_" + artifact_version_id
            assert edge_id in edge_id_to_model_mapping
            edge = edge_id_to_model_mapping[edge_id]
            assert edge.source == step_id
            assert edge.target == artifact_version_id

        # Check that each step node is connected to all of its input nodes
        for input_artifact in step_.inputs.values():
            artifact_version_id = ARTIFACT_PREFIX + str(input_artifact.id)
            assert artifact_version_id in node_id_to_model_mapping
            edge_id = artifact_version_id + "_" + step_id
            assert edge_id in edge_id_to_model_mapping
            edge = edge_id_to_model_mapping[edge_id]
            assert edge.source == artifact_version_id
            assert edge.target == step_id
