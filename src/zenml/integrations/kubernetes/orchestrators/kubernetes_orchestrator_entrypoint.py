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
import time
from collections import defaultdict
from typing import Any, Dict, List

from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_base_pod_manifest,
    update_pod_manifest,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


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
    sorted_steps = pipeline_config["sorted_steps"]
    fixed_step_args = pipeline_config["fixed_step_args"]
    step_specific_args = pipeline_config["step_specific_args"]
    step_dependencies = pipeline_config["step_dependencies"]

    # Revert step dependencies so we can easily get subsequent steps of a step.
    step_successors = defaultdict(list)
    for step_name, deps in step_dependencies.items():
        for previous_step_name in deps:
            step_successors[previous_step_name].append(step_name)

    # Get k8s Core API for running kubectl commands later.
    core_api = kube_utils.make_core_v1_api()

    # Build base pod manifest.
    base_pod_manifest = build_base_pod_manifest(
        run_name=args.run_name,
        pipeline_name=args.pipeline_name,
        image_name=args.image_name,
    )

    class StepDependencies:
        """Class to wrap step_dependencies for multi-threading."""

        def __init__(self, step_dependencies: Dict[str, List[str]]) -> None:
            self.step_dependencies = step_dependencies
            self._lock = threading.Lock()

        def get_dependencies(self, step_name: str) -> List[str]:
            """Get a list of all dependencies of a step.

            Args:
                step_name (str): Name of the step whose dependencies to get.

            Returns:
                List[str]: List of step names on which the given step depends.
            """
            with self._lock:
                return self.step_dependencies[step_name]

        def remove_dependency(self, step_name: str, dependency: str) -> None:
            """Remove a dependency of a step.

            Args:
                step_name (str): Name of the step.
                dependency (str): Name of the dependency (other step).
            """
            with self._lock:
                self.step_dependencies[step_name].remove(dependency)

    # wrap step dependencies in a class to enable multi-threaded updates.
    step_dependencies = StepDependencies(step_dependencies)

    class ThreadDict(dict):  # type: ignore[type-arg]
        """Thread-safe dict used to keep track of all threads per step."""

        def __init__(self) -> None:
            super().__init__()
            self._lock = threading.Lock()

        def __setitem__(self, __k: Any, __v: Any) -> None:
            with self._lock:
                super().__setitem__(__k, __v)

        def __delitem__(self, __k: Any) -> None:
            with self._lock:
                super().__delitem__(__k)

    # dict {step: thread} to keep track of currently running threads
    thread_dict = ThreadDict()

    def _can_run(step_name: str) -> bool:
        """Return whether a step has no dependencies and can run now.

        Args:
            step_name (str): Name of the step.

        Returns:
            bool: True if step can run now else False.
        """
        dependencies = step_dependencies.get_dependencies(step_name)
        return len(dependencies) == 0

    def _run_step(step_name: str) -> None:
        """Run a single step.

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

        # Remove current step from all dependencies and start next steps.
        for successor_step_name in step_successors[step_name]:
            step_dependencies.remove_dependency(successor_step_name, step_name)
            if _can_run(successor_step_name):
                _run_step_in_thread(successor_step_name)

        del thread_dict[step_name]  # remove current thread

    def _run_step_in_thread(step_name: str) -> None:
        """Call _run_step() in a separate thread.

        Args:
            step_name (str): Name of the step to run.
        """
        thread = threading.Thread(target=_run_step, args=(step_name,))
        thread_dict[step_name] = thread
        thread.start()

    # Run all steps that have no dependencies and can be started immediately.
    # These will, in turn, start other steps once all of their respective
    # dependencies have run.
    source_steps = [step for step in sorted_steps if _can_run(step)]
    for step_name in source_steps:
        _run_step_in_thread(step_name)

    # Wait till all steps have run
    while len(thread_dict) > 0:
        logger.debug(f"Waiting for threads: {thread_dict}")
        time.sleep(1)

    # Make sure all steps were run, otherwise print a warning.
    for step_name in sorted_steps:
        if not _can_run(step_name):
            logger.warning(
                f"Step `{step_name}` was never run, because it still had the "
                f"following dependencies: `{deps}`."
            )

    logger.info("Orchestration pod completed.")


if __name__ == "__main__":
    main()
