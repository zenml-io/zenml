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
"""Utilities for topological sort.

Implementation heavily inspired by TFX:
https://github.com/tensorflow/tfx/blob/master/tfx/utils/topsort.py
"""

from typing import Callable, List, Sequence, TypeVar

from zenml.logger import get_logger

logger = get_logger(__name__)

NodeT = TypeVar("NodeT")


def topsorted_layers(
    nodes: Sequence[NodeT],
    get_node_id_fn: Callable[[NodeT], str],
    get_parent_nodes: Callable[[NodeT], List[NodeT]],
    get_child_nodes: Callable[[NodeT], List[NodeT]],
) -> List[List[NodeT]]:
    """Sorts the DAG of nodes in topological order.

    Args:
        nodes: A sequence of nodes.
        get_node_id_fn: Callable that returns a unique text identifier for a node.
        get_parent_nodes: Callable that returns a list of parent nodes for a node.
            If a parent node's id is not found in the list of node ids, that parent
            node will be omitted.
        get_child_nodes: Callable that returns a list of child nodes for a node.
            If a child node's id is not found in the list of node ids, that child
            node will be omitted.

    Returns:
        A list of topologically ordered node layers. Each layer of nodes is sorted
        by its node id given by `get_node_id_fn`.

    Raises:
        RuntimeError: If the input nodes don't form a DAG.
        ValueError: If the nodes are not unique.
    """
    # Make sure the nodes are unique.
    node_ids = set(get_node_id_fn(n) for n in nodes)
    if len(node_ids) != len(nodes):
        raise ValueError("Nodes must have unique ids.")

    # The outputs of get_(parent|child)_nodes should always be deduplicated,
    # and references to unknown nodes should be removed.
    def _apply_and_clean(
        func: Callable[[NodeT], List[NodeT]], func_name: str, node: NodeT
    ) -> List[NodeT]:
        seen_inner_node_ids = set()
        result = []
        for inner_node in func(node):
            inner_node_id = get_node_id_fn(inner_node)
            if inner_node_id in seen_inner_node_ids:
                logger.warning(
                    "Duplicate node_id %s found when calling %s on node %s. "
                    "This entry will be ignored.",
                    inner_node_id,
                    func_name,
                    node,
                )
            elif inner_node_id not in node_ids:
                logger.warning(
                    "node_id %s found when calling %s on node %s, but this node_id is "
                    "not found in the set of input nodes %s. This entry will be "
                    "ignored.",
                    inner_node_id,
                    func_name,
                    node,
                    node_ids,
                )
            else:
                seen_inner_node_ids.add(inner_node_id)
                result.append(inner_node)

        return result

    def get_clean_parent_nodes(node: NodeT) -> List[NodeT]:
        return _apply_and_clean(get_parent_nodes, "get_parent_nodes", node)

    def get_clean_child_nodes(node: NodeT) -> List[NodeT]:
        return _apply_and_clean(get_child_nodes, "get_child_nodes", node)

    # The first layer contains nodes with no incoming edges.
    layer = [node for node in nodes if not get_clean_parent_nodes(node)]

    visited_node_ids = set()
    layers = []
    while layer:
        layer = sorted(layer, key=get_node_id_fn)
        layers.append(layer)

        next_layer = []
        for node in layer:
            visited_node_ids.add(get_node_id_fn(node))
            for child_node in get_clean_child_nodes(node):
                # Include the child node if all its parents are visited. If the child
                # node is part of a cycle, it will never be included since it will have
                # at least one unvisited parent node which is also part of the cycle.
                parent_node_ids = set(
                    get_node_id_fn(p)
                    for p in get_clean_parent_nodes(child_node)
                )
                if parent_node_ids.issubset(visited_node_ids):
                    next_layer.append(child_node)
        layer = next_layer

    num_output_nodes = sum(len(layer) for layer in layers)
    # Nodes in cycles are not included in layers; raise an error if this happens.
    if num_output_nodes < len(nodes):
        raise RuntimeError("Cannot sort graph because it contains a cycle.")
    # This should never happen; raise an error if this occurs.
    if num_output_nodes > len(nodes):
        raise RuntimeError("Unknown error occurred while sorting DAG.")

    return layers
