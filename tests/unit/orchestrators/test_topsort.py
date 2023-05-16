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
#
# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for `zenml.orchestrators.topsort.py`.

Implementation heavily inspired by TFX:
https://github.com/tensorflow/tfx/blob/master/tfx/utils/topsort_test.py
"""

import attr
import pytest

from zenml.orchestrators.topsort import topsorted_layers


@attr.s
class Node:
    """An unhashable class for testing."""

    name = attr.ib()
    upstream_nodes = attr.ib()
    downstream_nodes = attr.ib()


def test_topsorted_layers_DAG():
    """Test the topological sort for a nice clean DAG."""
    nodes = [
        Node("A", [], ["B", "C", "D"]),
        Node("B", ["A"], []),
        Node("C", ["A"], ["D"]),
        Node("D", ["A", "C", "F"], ["E"]),
        Node("E", ["D"], []),
        Node("F", [], ["D"]),
    ]
    node_map = {node.name: node for node in nodes}
    layers = topsorted_layers(
        nodes,
        get_node_id_fn=lambda n: n.name,
        get_parent_nodes=(
            lambda n: [node_map[name] for name in n.upstream_nodes]
        ),
        get_child_nodes=(
            lambda n: [node_map[name] for name in n.downstream_nodes]
        ),
    )
    result = [[node.name for node in layer] for layer in layers]
    expected_result = [["A", "F"], ["B", "C"], ["D"], ["E"]]
    assert result == expected_result


def test_topsorted_layers_error_if_cycle():
    """Test that the topological sort raises an error if there is a cycle."""
    nodes = [
        Node("A", [], ["B", "E"]),
        Node("B", ["A", "D"], ["C"]),
        Node("C", ["B"], ["D"]),
        Node("D", ["C"], ["B"]),
        Node("E", ["A"], []),
    ]
    node_map = {node.name: node for node in nodes}
    with pytest.raises(RuntimeError):
        topsorted_layers(
            nodes,
            get_node_id_fn=lambda n: n.name,
            get_parent_nodes=(
                lambda n: [node_map[name] for name in n.upstream_nodes]
            ),
            get_child_nodes=(
                lambda n: [node_map[name] for name in n.downstream_nodes]
            ),
        )


def test_topsorted_layers_ignore_unknown_parent_node():
    """Test that the topological sort simply ignores unknown parent nodes."""
    nodes = [
        Node("A", [], ["B"]),
        Node("B", ["A"], ["C"]),
        Node("C", ["B"], []),
    ]
    node_map = {node.name: node for node in nodes}
    # Exclude node A. Node B now has a parent node 'A' that should be ignored.
    layers = topsorted_layers(
        [node_map["B"], node_map["C"]],
        get_node_id_fn=lambda n: n.name,
        get_parent_nodes=(
            lambda n: [node_map[name] for name in n.upstream_nodes]
        ),
        get_child_nodes=(
            lambda n: [node_map[name] for name in n.downstream_nodes]
        ),
    )
    result = [[node.name for node in layer] for layer in layers]
    expected_result = [["B"], ["C"]]
    assert result == expected_result


def test_topsorted_layers_ignore_duplicate_parent_node():
    """Test that the topological sort simply ignores duplicate parent nodes."""
    nodes = [
        Node("A", [], ["B"]),
        Node("B", ["A", "A"], []),  # Duplicate parent node 'A'
    ]
    node_map = {node.name: node for node in nodes}
    layers = topsorted_layers(
        nodes,
        get_node_id_fn=lambda n: n.name,
        get_parent_nodes=(
            lambda n: [node_map[name] for name in n.upstream_nodes]
        ),
        get_child_nodes=(
            lambda n: [node_map[name] for name in n.downstream_nodes]
        ),
    )
    result = [[node.name for node in layer] for layer in layers]
    expected_result = [["A"], ["B"]]
    assert result == expected_result


def test_topsorted_layers_ignore_unknown_child_node():
    """Test that the topological sort simply ignores unknown child nodes."""
    nodes = [
        Node("A", [], ["B"]),
        Node("B", ["A"], ["C"]),
        Node("C", ["B"], []),
    ]
    node_map = {node.name: node for node in nodes}
    # Exclude node C. Node B now has a child node 'C' that should be ignored.
    layers = topsorted_layers(
        [node_map["A"], node_map["B"]],
        get_node_id_fn=lambda n: n.name,
        get_parent_nodes=(
            lambda n: [node_map[name] for name in n.upstream_nodes]
        ),
        get_child_nodes=(
            lambda n: [node_map[name] for name in n.downstream_nodes]
        ),
    )
    result = [[node.name for node in layer] for layer in layers]
    expected_result = [["A"], ["B"]]
    assert result == expected_result


def test_topsorted_layers_ignore_duplicate_child_node():
    """Test that the topological sort simply ignores duplicate child nodes."""
    nodes = [
        Node("A", [], ["B", "B"]),  # Duplicate child node 'B'
        Node("B", ["A"], []),
    ]
    node_map = {node.name: node for node in nodes}
    layers = topsorted_layers(
        nodes,
        get_node_id_fn=lambda n: n.name,
        get_parent_nodes=(
            lambda n: [node_map[name] for name in n.upstream_nodes]
        ),
        get_child_nodes=(
            lambda n: [node_map[name] for name in n.downstream_nodes]
        ),
    )
    result = [[node.name for node in layer] for layer in layers]
    expected_result = [["A"], ["B"]]
    assert result == expected_result


def test_topsorted_layers_empty():
    """Test that the topological sort works with an empty list of nodes."""
    layers = topsorted_layers(
        nodes=[],
        get_node_id_fn=lambda n: n.name,
        get_parent_nodes=lambda n: [],
        get_child_nodes=lambda n: [],
    )
    assert layers == []
