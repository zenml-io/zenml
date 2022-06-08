import threading
from collections import defaultdict
from typing import Dict, List

from zenml.logger import get_logger

logger = get_logger(__name__)


class ThreadedDagRunner:
    """Class to wrap pipeline_dag for multi-threading."""

    def __init__(self, dag: Dict[str, List[str]], run_fn) -> None:
        self.dag = dag
        self.reversed_dag = self.reverse_dag(dag)
        self.run_fn = run_fn
        self.nodes = dag.keys()
        self.node_is_waiting = {node_name: True for node_name in self.nodes}
        self.node_is_running = {node_name: False for node_name in self.nodes}
        self.node_is_completed = {node_name: False for node_name in self.nodes}
        self._lock = threading.Lock()

    @staticmethod
    def reverse_dag(dag):
        """Reverse a DAG."""
        reversed_dag = defaultdict(list)
        for node_name, upstream_nodes in dag.items():
            for upstream_node in upstream_nodes:
                reversed_dag[upstream_node].append(node_name)
        return reversed_dag

    def _can_run(self, node: str) -> bool:
        """Return whether a node is ready to be run.

        This is the case if the node has not run yet and all of its upstream
        node have already completed.

        Args:
            node (str): Name of the node.

        Returns:
            bool: True if node can run else False.
        """
        if not self.node_is_waiting[node]:
            return False
        for upstream_node in self.dag[node]:
            if not self.node_is_completed[upstream_node]:
                return False
        return True

    def _run_node(self, node):
        # run the node using the user-defined run_fn
        self.run_fn(node)

        # finish node
        self._finish_node(node)

    def _run_node_in_thread(self, node):
        # update node status to running
        assert self.node_is_waiting[node]
        with self._lock:
            self.node_is_waiting[node] = False
            self.node_is_running[node] = True

        # run node in new thread
        thread = threading.Thread(target=self._run_node, args=(node,))
        thread.start()
        return thread

    def _finish_node(self, node):
        # update node status to completed
        assert self.node_is_running[node]
        with self._lock:
            self.node_is_running[node] = False
            self.node_is_completed[node] = True

        # run downstream nodes
        threads = []
        for downstram_node in self.reversed_dag[node]:
            if self._can_run(downstram_node):
                thread = self._run_node_in_thread(downstram_node)
                threads.append(thread)

        # wait for all downstream nodes to complete
        for thread in threads:
            thread.join()

    def run(self):
        # Run all nodes that can be started immediately.
        # These will, in turn, start other nodes once all of their respective
        # upstream nodes have run.
        threads = []
        for node in self.nodes:
            if self._can_run(node):
                thread = self._run_node_in_thread(node)
                threads.append(thread)

        # Wait till all nodes have completed.
        for thread in threads:
            thread.join()

        # Make sure all nodes were run, otherwise print a warning.
        for node in self.nodes:
            if self.node_is_waiting[node]:
                upstream_nodes = self.dag[node]
                logger.warning(
                    f"Node `{node}` was never run, because it was still"
                    f" waiting for the following nodes: `{upstream_nodes}`."
                )
