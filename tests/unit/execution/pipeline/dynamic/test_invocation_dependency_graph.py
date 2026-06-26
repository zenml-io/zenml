#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Unit tests for the invocation dependency graph."""

from zenml import pipeline, step
from zenml.execution.pipeline.dynamic.invocation_dependency_graph import (
    InvocationDependencyGraph,
    NodeState,
)


@step
def _noop_step() -> None:
    pass


@pipeline(dynamic=True)
def _noop_pipeline() -> None:
    pass


def _start_step(graph: InvocationDependencyGraph, node_id: str) -> None:
    """Drive a step node from ready to running."""
    graph.mark_node_starting(node_id)
    graph.mark_node_running(node_id)


def test_after_requires_success_not_just_start() -> None:
    """An `after` dependency releases only when the upstream succeeds."""
    graph = InvocationDependencyGraph()
    graph.register_step_node(node_id="a")
    graph.register_step_node(node_id="b", upstream_ids=["a"])

    _start_step(graph, "a")
    assert graph.get_node_state("b") == NodeState.PENDING

    graph.mark_node_succeeded("a")
    assert graph.get_node_state("b") == NodeState.READY


def test_start_after_blocks_until_running() -> None:
    """A starting (not yet running) upstream does not release a dependent."""
    graph = InvocationDependencyGraph()
    graph.register_step_node(node_id="a")
    graph.register_step_node(node_id="b", start_upstream_ids=["a"])

    graph.mark_node_starting("a")
    # The upstream is being launched but is not running yet.
    assert graph.get_node_state("b") == NodeState.PENDING

    graph.mark_node_running("a")
    assert graph.get_node_state("b") == NodeState.READY


def test_start_after_releases_when_upstream_runs() -> None:
    """A `start_after` dependency releases when the upstream runs."""
    graph = InvocationDependencyGraph()
    graph.register_step_node(node_id="a")
    _, ready = graph.register_step_node(node_id="b", start_upstream_ids=["a"])
    assert ready is False
    assert graph.get_node_state("b") == NodeState.PENDING

    graph.mark_node_starting("a")
    became_ready = graph.mark_node_running("a")
    assert became_ready is True
    assert graph.get_node_state("b") == NodeState.READY


def test_start_after_released_when_upstream_already_running() -> None:
    """A `start_after` dependency on an already-running upstream is ready."""
    graph = InvocationDependencyGraph()
    graph.register_step_node(node_id="a")
    _start_step(graph, "a")

    _, ready = graph.register_step_node(node_id="b", start_upstream_ids=["a"])
    assert ready is True
    assert graph.get_node_state("b") == NodeState.READY


def test_start_after_released_by_cached_upstream() -> None:
    """A `start_after` dependency on a cached upstream is ready."""
    graph = InvocationDependencyGraph()
    graph.register_step_node(node_id="a", state=NodeState.SUCCEEDED)

    _, ready = graph.register_step_node(node_id="b", start_upstream_ids=["a"])
    assert ready is True
    assert graph.get_node_state("b") == NodeState.READY


def test_start_after_released_by_failed_upstream() -> None:
    """A failed upstream counts as started for a `start_after` dependency."""
    graph = InvocationDependencyGraph()
    graph.register_step_node(node_id="a")
    graph.register_step_node(node_id="b", start_upstream_ids=["a"])

    graph.mark_node_starting("a")
    became_ready = graph.mark_node_failed("a")
    assert became_ready is True
    assert graph.get_node_state("b") == NodeState.READY


def test_mixed_after_and_start_after() -> None:
    """A node with both dependency kinds waits for both to be satisfied."""
    graph = InvocationDependencyGraph()
    graph.register_step_node(node_id="a")
    graph.register_step_node(node_id="c")
    graph.register_step_node(
        node_id="b", upstream_ids=["a"], start_upstream_ids=["c"]
    )

    _start_step(graph, "c")
    # `c` is running, but `a` has not succeeded yet.
    assert graph.get_node_state("b") == NodeState.PENDING

    _start_step(graph, "a")
    graph.mark_node_succeeded("a")
    assert graph.get_node_state("b") == NodeState.READY


def test_start_after_map_node_releases_when_running() -> None:
    """A `start_after` dependency on a map node releases when it runs."""
    graph = InvocationDependencyGraph()
    graph.register_map_node(
        node_id="m", step=_noop_step, inputs={}, product=False
    )
    graph.register_step_node(node_id="b", start_upstream_ids=["m"])
    assert graph.get_node_state("b") == NodeState.PENDING

    graph.mark_node_starting("m")
    became_ready = graph.mark_node_running("m")
    assert became_ready is True
    assert graph.get_node_state("b") == NodeState.READY


def test_start_after_child_pipeline_releases_when_running() -> None:
    """A `start_after` dependency on a child pipeline releases when it runs."""
    graph = InvocationDependencyGraph()
    graph.register_child_pipeline_node(node_id="c", pipeline=_noop_pipeline)
    graph.register_step_node(node_id="b", start_upstream_ids=["c"])
    assert graph.get_node_state("b") == NodeState.PENDING
    assert graph.node_has_started("c") is False

    graph.mark_node_starting("c")
    became_ready = graph.mark_node_running("c")
    assert became_ready is True
    assert graph.node_has_started("c") is True
    assert graph.get_node_state("b") == NodeState.READY
