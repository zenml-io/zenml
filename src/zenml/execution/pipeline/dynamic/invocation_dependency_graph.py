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
"""Invocation dependency graph."""

import threading
from dataclasses import dataclass, field
from typing import Any, Collection, Dict, List, Optional, Sequence, Set, Union

from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.execution.pipeline.dynamic.outputs import AnyStepFuture
from zenml.logger import get_logger
from zenml.steps import BaseStep
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)


class NodeState(StrEnum):
    """Invocation dependency graph node state."""

    PENDING = "pending"
    READY = "ready"
    STARTING = "starting"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        """Whether the state is terminal.

        Returns:
            True if the state is terminal, False otherwise.
        """
        return self in {
            NodeState.SUCCEEDED,
            NodeState.FAILED,
        }


@dataclass(kw_only=True)
class BaseNode:
    """Base node in the dependency graph."""

    node_id: str
    state: NodeState = NodeState.PENDING
    upstream_ids: Set[str] = field(default_factory=set)
    downstream_ids: Set[str] = field(default_factory=set)

    @property
    def is_terminal(self) -> bool:
        """Whether the node is terminal.

        Returns:
            True if the node is terminal, False otherwise.
        """
        return self.state.is_terminal


@dataclass(kw_only=True)
class StepNode(BaseNode):
    """Step graph node."""

    parent_id: Optional[str] = None
    step: Optional[BaseStep] = None
    inputs: Optional[Dict[str, Any]] = None
    after: Optional[Union[AnyStepFuture, Sequence[AnyStepFuture]]] = None
    config_overrides: Optional["StepConfigurationUpdate"] = None


@dataclass(kw_only=True)
class MapNode(BaseNode):
    """Map graph node."""

    child_node_ids: Set[str] = field(default_factory=set)
    step: BaseStep
    inputs: Dict[str, Any]
    after: Union[AnyStepFuture, Sequence[AnyStepFuture], None]
    product: bool


AnyNode = Union[StepNode, MapNode]


class InvocationDependencyGraph:
    """Invocation dependency graph."""

    def __init__(self) -> None:
        """Initialize the graph."""
        self._lock = threading.RLock()
        self._nodes: Dict[str, AnyNode] = {}

    def register_step_node(
        self,
        node_id: str,
        upstream_ids: Optional[Sequence[str]] = None,
        state: Optional[NodeState] = None,
        step: Optional[BaseStep] = None,
        inputs: Optional[Dict[str, Any]] = None,
        after: Optional[Union[AnyStepFuture, Sequence[AnyStepFuture]]] = None,
        config_overrides: Optional["StepConfigurationUpdate"] = None,
    ) -> bool:
        """Register a step node.

        Args:
            node_id: The node ID.
            upstream_ids: Optional upstream node IDs.
            state: Optional initial state for the node.
            step: Optional step payload for startup.
            inputs: Optional input payload for startup.
            after: Optional `after` payload for startup.
            config_overrides: Optional config overrides for startup.

        Returns:
            Whether the registration caused any newly ready nodes.
        """
        node = StepNode(
            node_id=node_id,
            state=state or NodeState.PENDING,
            step=step,
            inputs=inputs,
            after=after,
            config_overrides=config_overrides,
        )
        return self._register_node(node=node, upstream_ids=upstream_ids)

    def register_map_node(
        self,
        node_id: str,
        step: BaseStep,
        inputs: Dict[str, Any],
        product: bool,
        upstream_ids: Optional[Sequence[str]] = None,
        state: Optional[NodeState] = None,
        after: Optional[Union[AnyStepFuture, Sequence[AnyStepFuture]]] = None,
    ) -> bool:
        """Register a map aggregate node.

        Args:
            node_id: The graph node ID.
            upstream_ids: Optional upstream node IDs.
            state: Optional initial state for the node.
            step: The mapped step payload for startup.
            inputs: The input payload for startup.
            after: Optional `after` payload for startup.
            product: The map expansion mode.

        Returns:
            Whether the registration caused any newly ready nodes.
        """
        node = MapNode(
            node_id=node_id,
            state=state or NodeState.PENDING,
            step=step,
            inputs=inputs,
            after=after,
            product=product,
        )
        return self._register_node(node=node, upstream_ids=upstream_ids)

    def get_step_node(self, node_id: str) -> StepNode:
        """Get a step node by ID.

        Args:
            node_id: The node ID.

        Raises:
            RuntimeError: If the node does not exist or is not a step node.

        Returns:
            The step node.
        """
        with self._lock:
            node = self._get_node(node_id=node_id)
            if not isinstance(node, StepNode):
                raise RuntimeError(f"Node `{node_id}` is not a step node.")
            return node

    def get_map_node(self, node_id: str) -> MapNode:
        """Get a map node by ID.

        Args:
            node_id: The node ID.

        Raises:
            RuntimeError: If the node does not exist or is not a map node.

        Returns:
            The map node.
        """
        with self._lock:
            node = self._get_node(node_id=node_id)
            if not isinstance(node, MapNode):
                raise RuntimeError(f"Node `{node_id}` is not a map node.")
            return node

    def attach_map_children(
        self, map_node_id: str, child_node_ids: Sequence[str]
    ) -> bool:
        """Attach expanded child nodes to a map node.

        Args:
            map_node_id: The map node ID.
            child_node_ids: The child step node IDs created by the expansion.

        Returns:
            Whether the attachment caused any newly ready nodes.
        """
        with self._lock:
            map_node = self.get_map_node(node_id=map_node_id)
            should_wake_startup_loop = False

            if map_node.state in {NodeState.READY, NodeState.STARTING}:
                self._set_node_state(
                    node_id=map_node_id, state=NodeState.RUNNING
                )

            for child_node_id in child_node_ids:
                child_node = self.get_step_node(node_id=child_node_id)
                map_node.child_node_ids.add(child_node_id)
                child_node.parent_id = map_node_id

            if not child_node_ids:
                should_wake_startup_loop = self._set_node_state(
                    node_id=map_node_id, state=NodeState.SUCCEEDED
                )
            else:
                should_wake_startup_loop = self._maybe_finalize_map_node(
                    map_node_id=map_node_id
                )

            return should_wake_startup_loop

    def list_nodes(
        self, states: Optional[Collection[NodeState]] = None
    ) -> List[AnyNode]:
        """List graph nodes in insertion order.

        Args:
            states: Optional node states to filter by.

        Returns:
            The graph nodes in insertion order.
        """
        with self._lock:
            return [
                node
                for node in self._nodes.values()
                if states is None or node.state in states
            ]

    def get_ready_node(self) -> Optional[AnyNode]:
        """Get one ready node in insertion order.

        Step nodes are prioritized over map nodes.

        Returns:
            A ready node if one exists, otherwise `None`.
        """
        with self._lock:
            ready_map_node: Optional[MapNode] = None
            for node in self._nodes.values():
                if node.state != NodeState.READY:
                    continue
                if isinstance(node, StepNode):
                    return node
                if isinstance(node, MapNode) and ready_map_node is None:
                    ready_map_node = node

            return ready_map_node

    def mark_node_starting(self, node_id: str) -> bool:
        """Mark a node as starting.

        Args:
            node_id: The node ID.

        Returns:
            Whether the transition caused any newly ready nodes.
        """
        return self._set_node_state(node_id=node_id, state=NodeState.STARTING)

    def mark_node_running(self, node_id: str) -> bool:
        """Mark a node as running.

        Args:
            node_id: The node ID.

        Returns:
            Whether the transition caused any newly ready nodes.
        """
        return self._set_node_state(node_id=node_id, state=NodeState.RUNNING)

    def mark_node_succeeded(self, node_id: str) -> bool:
        """Mark a node as successful.

        Args:
            node_id: The node ID.

        Returns:
            Whether the transition caused any newly ready nodes.
        """
        return self._set_node_state(node_id=node_id, state=NodeState.SUCCEEDED)

    def mark_node_failed(self, node_id: str) -> bool:
        """Mark a node as failed.

        Args:
            node_id: The node ID.

        Returns:
            Whether the transition caused any newly ready nodes.
        """
        return self._set_node_state(node_id=node_id, state=NodeState.FAILED)

    def _register_node(
        self,
        node: AnyNode,
        upstream_ids: Optional[Sequence[str]],
    ) -> bool:
        """Register a graph node.

        Args:
            node: The node to register.
            upstream_ids: Optional upstream node IDs.

        Raises:
            RuntimeError: If an upstream node is unknown or a node with the same
                ID but a different node type already exists.

        Returns:
            Whether the registration caused any newly ready nodes.
        """
        with self._lock:
            if existing_node := self._nodes.get(node.node_id):
                if type(existing_node) is not type(node):
                    raise RuntimeError(
                        f"Node `{node.node_id}` already exists as a different "
                        "node type."
                    )
                return False

            self._nodes[node.node_id] = node

            for upstream_id in upstream_ids or []:
                self._get_node(node_id=upstream_id)
                node.upstream_ids.add(upstream_id)
                self._nodes[upstream_id].downstream_ids.add(node.node_id)

            if node.state == NodeState.READY:
                return True

            if node.state.is_terminal:
                return self._handle_terminal_node_transition(
                    node_id=node.node_id
                )

            return self._maybe_mark_node_ready(node_id=node.node_id)

    def _validate_node_state_transition(
        self, old_state: NodeState, new_state: NodeState
    ) -> NodeState:
        """Validate a node state transition.

        Args:
            old_state: The old state.
            new_state: The new state.

        Raises:
            RuntimeError: If the state transition is invalid.

        Returns:
            The validated new state.
        """
        if old_state == new_state:
            return new_state

        if old_state.is_terminal and new_state == NodeState.RUNNING:
            # Ignore potentially late updates that can happen if concurrent
            # execution finishes first.
            logger.debug(
                "Ignore state transition from terminal state `%s` to `%s`.",
                old_state,
                new_state,
            )
            return old_state

        if old_state.is_terminal:
            raise RuntimeError(
                f"Invalid state transition from `{old_state}` to `{new_state}`."
            )

        if new_state == NodeState.STARTING and old_state != NodeState.READY:
            raise RuntimeError(
                f"Invalid state transition from `{old_state}` to `{new_state}`."
            )

        if new_state == NodeState.RUNNING and old_state != NodeState.STARTING:
            raise RuntimeError(
                f"Invalid state transition from `{old_state}` to `{new_state}`."
            )

        return new_state

    def _set_node_state(self, node_id: str, state: NodeState) -> bool:
        """Set a node state and propagate side effects.

        Args:
            node_id: The node ID.
            state: The target state.

        Returns:
            Whether the transition caused any newly ready nodes.
        """
        with self._lock:
            node = self._get_node(node_id=node_id)
            old_state = node.state

            node.state = self._validate_node_state_transition(
                old_state=old_state, new_state=state
            )

            if node.state == old_state:
                return False

            if node.state.is_terminal:
                return self._handle_terminal_node_transition(node_id=node_id)

            return node.state == NodeState.READY

    def _handle_terminal_node_transition(self, node_id: str) -> bool:
        """Handle a terminal node transition.

        Args:
            node_id: The node ID.

        Returns:
            Whether the transition caused any newly ready nodes.
        """
        node = self._get_node(node_id=node_id)

        new_nodes_ready = False

        parent_map_id = node.parent_id if isinstance(node, StepNode) else None
        if parent_map_id:
            new_nodes_ready = self._maybe_finalize_map_node(
                map_node_id=parent_map_id
            )

        for downstream_id in node.downstream_ids:
            new_nodes_ready = (
                self._maybe_mark_node_ready(node_id=downstream_id)
                or new_nodes_ready
            )

        return new_nodes_ready

    def _maybe_finalize_map_node(self, map_node_id: str) -> bool:
        """Finalize a map node once all child nodes are terminal.

        Args:
            map_node_id: The map node ID.

        Returns:
            Whether finalizing the map node caused any newly ready nodes.
        """
        map_node = self.get_map_node(node_id=map_node_id)

        if map_node.state.is_terminal:
            return False

        if not map_node.child_node_ids:
            return False

        child_nodes = [
            self._get_node(node_id=child_node_id)
            for child_node_id in map_node.child_node_ids
        ]
        if not all(child_node.is_terminal for child_node in child_nodes):
            return False

        if any(
            child_node.state == NodeState.FAILED for child_node in child_nodes
        ):
            aggregate_state = NodeState.FAILED
        else:
            aggregate_state = NodeState.SUCCEEDED

        return self._set_node_state(node_id=map_node_id, state=aggregate_state)

    def _maybe_mark_node_ready(self, node_id: str) -> bool:
        """Mark a pending node as ready when all upstream nodes succeeded.

        Args:
            node_id: The node ID.

        Returns:
            Whether the node became ready.
        """
        node = self._get_node(node_id=node_id)
        if node.state != NodeState.PENDING:
            return False

        if not all(
            self._get_node(node_id=upstream_id).state == NodeState.SUCCEEDED
            for upstream_id in node.upstream_ids
        ):
            return False

        self._set_node_state(node_id=node_id, state=NodeState.READY)
        return True

    def _get_node(self, node_id: str) -> AnyNode:
        """Get a node without acquiring the lock.

        Args:
            node_id: The node ID.

        Raises:
            RuntimeError: If the node does not exist.

        Returns:
            The graph node.
        """
        node = self._nodes.get(node_id)
        if not node:
            raise RuntimeError(f"Unknown graph node `{node_id}`.")
        return node
