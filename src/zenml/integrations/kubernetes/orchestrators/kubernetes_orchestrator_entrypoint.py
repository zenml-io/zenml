"""Entrypoint of the k8s master/orchestrator pod."""

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

import argparse
import json
import threading
from collections import defaultdict
from typing import Dict, List

from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_base_pod_manifest,
    update_pod_manifest,
)
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


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        argparse.Namespace: Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_name", type=str, required=True)
    parser.add_argument("--pipeline_name", type=str, required=True)
    parser.add_argument("--image_name", type=str, required=True)
    parser.add_argument("--kubernetes_namespace", type=str, required=True)
    parser.add_argument("--pipeline_config", type=json.loads, required=True)
    return parser.parse_args()


def main() -> None:
    """Entrypoint of the k8s master/orchestrator pod."""
    # Log to the container's stdout so it can be streamed by the client.
    logger.info("Kubernetes orchestrator pod started.")

    # Parse / extract args.
    args = parse_args()
    pipeline_config = args.pipeline_config
    step_command = pipeline_config["step_command"]
    fixed_step_args = pipeline_config["fixed_step_args"]
    step_specific_args = pipeline_config["step_specific_args"]
    pipeline_dag = pipeline_config["pipeline_dag"]

    # Get k8s Core API for running kubectl commands later.
    core_api = kube_utils.make_core_v1_api()

    # Build base pod manifest.
    base_pod_manifest = build_base_pod_manifest(
        run_name=args.run_name,
        pipeline_name=args.pipeline_name,
        image_name=args.image_name,
    )

    def run_step_on_kubernetes(step_name: str) -> None:
        """Run a pipeline step in a separate Kubernetes pod.

        Args:
            step_name (str): Name of the step.
        """
        # Define k8s pod name.
        pod_name = f"{args.run_name}-{step_name}"
        pod_name = kube_utils.sanitize_pod_name(pod_name)

        # Build list of args for this step.
        step_args = [*fixed_step_args, *step_specific_args[step_name]]

        # Define k8s pod manifest.
        pod_manifest = update_pod_manifest(
            base_pod_manifest=base_pod_manifest,
            pod_name=pod_name,
            command=step_command,
            args=step_args,
        )

        # Create and run pod.
        core_api.create_namespaced_pod(
            namespace=args.kubernetes_namespace,
            body=pod_manifest,
        )

        # Wait for pod to finish.
        logger.info(f"Waiting for pod of step `{step_name}` to start...")
        kube_utils.wait_pod(
            core_api,
            pod_name,
            namespace=args.kubernetes_namespace,
            exit_condition_lambda=kube_utils.pod_is_done,
            stream_logs=True,
        )
        logger.info(f"Pod of step `{step_name}` completed.")

    ThreadedDagRunner(dag=pipeline_dag, run_fn=run_step_on_kubernetes).run()

    logger.info("Orchestration pod completed.")


if __name__ == "__main__":
    main()
