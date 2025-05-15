# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2025. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import time
from typing import Any, Dict

import click

from zenml import Tag, get_step_context, log_metadata, pipeline, step
from zenml.client import Client
from zenml.config import DockerSettings
from zenml.config.docker_settings import PythonPackageInstaller
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings

kubernetes_settings = KubernetesOrchestratorSettings(
    pod_startup_timeout=600,
    pod_settings=KubernetesPodSettings(
        resources={
            "requests": {"cpu": "100m", "memory": "300Mi"},
            "limits": {"memory": "350Mi"},
        },
        node_selectors={"pool": "workloads"},
        tolerations=[
            {
                "key": "pool",
                "operator": "Equal",
                "value": "workloads",
                "effect": "NoSchedule",
            }
        ],
        env=[{"name": "ZENML_LOGGING_VERBOSITY", "value": "debug"}],
    ),
    orchestrator_pod_settings=KubernetesPodSettings(
        resources={
            "requests": {"cpu": "100m", "memory": "300Mi"},
            "limits": {"memory": "350Mi"},
        },
        node_selectors={"pool": "workloads"},
        tolerations=[
            {
                "key": "pool",
                "operator": "Equal",
                "value": "workloads",
                "effect": "NoSchedule",
            }
        ],
    ),
)

docker_settings = DockerSettings(
    python_package_installer=PythonPackageInstaller.UV,
)
settings = {"docker": docker_settings, "orchestrator": kubernetes_settings}


@step
def load_step(
    duration: int,
    sleep_interval: float,
) -> Dict[str, Any]:
    """A step that performs API operations to stress test the ZenML server.

    This step will perform a number of API operations to stress test the ZenML server.
    It will list pipeline runs, stacks, stack components, and service connectors.

    Args:
        duration: The duration of the load test in seconds.
        sleep_interval: The interval to sleep between API calls in seconds.

    Returns:
        A dictionary containing the number of operations performed and the
        duration of the test.
    """
    client = Client()
    start_time = time.time()
    operations = 0

    print("Adding metadata...")
    log_metadata(
        metadata={
            "key": "value",
            "key2": 2,
            "key3": [1, 2, 3],
            "key4": {
                "subkey": "subvalue",
                "some_list": [1, 2, 3],
                "some_dict": {"subkey2": "subvalue2"},
            },
            "key5": True,
            "key6": False,
            "key8": 1.0,
            "key9": 1.0,
        }
    )
    
    print("Starting API calls...")
    while time.time() - start_time < duration:
        # Perform various API operations
        print("Listing pipeline runs...")
        client.list_pipeline_runs()
        print("Listing stacks...")
        client.list_stacks()
        print("Listing stack components...")
        client.list_stack_components()
        print("Listing service connectors...")
        client.list_service_connectors()

        operations += 4
        if sleep_interval > 0:
            print(f"Sleeping for {sleep_interval} seconds...")
            time.sleep(sleep_interval)

    return {
        "operations": operations,
        "duration": duration,
    }


# The report results step is beefier than the load step because it has to fetch
# all the artifacts from the run.
report_kubernetes_settings = KubernetesOrchestratorSettings(
    pod_settings=KubernetesPodSettings(
        resources={
            "requests": {"cpu": "100m", "memory": "500Mi"},
            "limits": {"memory": "600Mi"},
        },
        node_selectors={"pool": "workloads"},
        tolerations=[
            {
                "key": "pool",
                "operator": "Equal",
                "value": "workloads",
                "effect": "NoSchedule",
            }
        ],
        env=[{"name": "ZENML_LOGGING_VERBOSITY", "value": "debug"}],
    ),
)

report_step_settings = {"orchestrator": report_kubernetes_settings}


@step(settings=report_step_settings)
def report_results() -> None:
    """A step that gathers and reports the results of the load test."""
    # Initialize the ZenML client to fetch artifacts
    context = get_step_context()
    current_run = context.pipeline_run

    # Get all steps from the current run
    steps = current_run.steps

    # Filter out the gather_results step itself and get results from load steps
    results = []
    for step_name, step_info in steps.items():
        if not step_name.startswith("load_step"):
            continue

        # Get the output artifact
        output = step_info.outputs.get("output")
        if output:
            # Get the actual artifact data using the client
            artifact_data = output[0].load()
            results.append(artifact_data)

    # Calculate metrics
    total_operations = sum(r["operations"] for r in results)
    avg_operations = total_operations / len(results) if results else 0

    print("\nLoad test completed!")
    print(f"Total operations: {total_operations}")
    print(f"Average operations per step: {avg_operations:.2f}")
    print(f"Number of steps: {len(results)}")


@pipeline(enable_cache=False, settings=settings)
def load_test_pipeline(
    num_parallel_steps: int, duration: int, sleep_interval: float
) -> None:
    """A pipeline that performs a load test on the ZenML server.

    This pipeline will spawn a number of parallel steps that will perform API
    operations to stress test the ZenML server.

    Args:
        num_parallel_steps: The number of parallel steps to run.
        duration: The duration of the load test in seconds.
        sleep_interval: The interval to sleep between API calls in seconds.
    """
    after = []
    for i in range(num_parallel_steps):
        after.append(load_step(duration, sleep_interval, id=f"load_step_{i}"))

    report_results(after=after)


@click.command()
@click.option(
    "--parallel-steps",
    "-p",
    default=5,
    help="Number of parallel steps to run",
    type=int,
    show_default=True,
)
@click.option(
    "--duration",
    "-d",
    default=300,
    help="Duration in seconds for each step to run",
    type=int,
    show_default=True,
)
@click.option(
    "--sleep-interval",
    "-s",
    default=0.1,
    help="Sleep interval between API calls in seconds",
    type=float,
    show_default=True,
)
@click.option(
    "--num-tags",
    "-t",
    default=10,
    help="Number of tags to add to the pipeline",
    type=int,
    show_default=True,
)
def main(
    parallel_steps: int, duration: int, sleep_interval: float, num_tags: int
) -> None:
    """Execute a ZenML load test with configurable parallel steps.

    This will spawn multiple parallel steps that continuously make API calls
    to stress test the ZenML server.

    Args:
        parallel_steps: The number of parallel steps to run.
        duration: The duration of the load test in seconds.
        sleep_interval: The interval to sleep between API calls in seconds.
        num_tags: The number of tags to add to the pipeline.
    """
    click.echo(f"Starting load test with {parallel_steps} parallel steps...")
    click.echo(f"Duration: {duration}s, Sleep Interval: {sleep_interval}s")

    load_test_pipeline.configure(
        tags=[Tag(name=f"tag_{i}", cascade=True) for i in range(num_tags)],
    )

    load_test_pipeline(
        num_parallel_steps=parallel_steps,
        duration=duration,
        sleep_interval=sleep_interval,
    )


if __name__ == "__main__":
    main()
