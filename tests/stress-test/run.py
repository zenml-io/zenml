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
from typing import Annotated, Any, Dict, Optional, Tuple

import click

from zenml import Tag, get_step_context, log_metadata, pipeline, step
from zenml.client import Client
from zenml.config import DockerSettings, StepRetryConfig
from zenml.config.docker_settings import PythonPackageInstaller
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings


def get_kubernetes_settings(
    max_parallelism: Optional[int],
) -> KubernetesOrchestratorSettings:
    """Get the Kubernetes settings for the ZenML server.

    Args:
        max_parallelism: The maximum number of parallel steps to run.

    Returns:
        The Kubernetes settings for the ZenML server.
    """
    return KubernetesOrchestratorSettings(
        service_account_name="zenml-service-account",
        max_parallelism=max_parallelism,
        backoff_limit_margin=3,
        pod_settings=KubernetesPodSettings(
            resources={
                "requests": {"cpu": "100m", "memory": "500Mi"},
                # "limits": {"memory": "500Mi"},    -> grows linearly with number of steps
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
            env=[
                {"name": "ZENML_LOGGING_VERBOSITY", "value": "debug"},
                {"name": "ZENML_ENABLE_RICH_TRACEBACK", "value": "false"},
            ],
        ),
        orchestrator_pod_settings=KubernetesPodSettings(
            resources={
                "requests": {"cpu": "100m", "memory": "500Mi"},
                # "limits": {"memory": "500Mi"}, # -> grows linearly with number of steps
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
settings = {"docker": docker_settings}


@step
def init_step() -> Tuple[
    Annotated[int, "output1"],
    Annotated[int, "output2"],
    Annotated[int, "output3"],
    Annotated[int, "output4"],
    Annotated[int, "output5"],
    Annotated[int, "output6"],
    Annotated[int, "output7"],
    Annotated[int, "output8"],
    Annotated[int, "output9"],
    Annotated[int, "output10"],
    Annotated[int, "output11"],
    Annotated[int, "output12"],
    Annotated[int, "output13"],
    Annotated[int, "output14"],
    Annotated[int, "output15"],
    Annotated[int, "output16"],
    Annotated[int, "output17"],
    Annotated[int, "output18"],
    Annotated[int, "output19"],
    Annotated[int, "output20"],
]:
    """A step that returns a bunch of outputs.

    This is used to test the performance of the ZenML server when returning
    a large number of outputs.

    Returns:
        A tuple of 20 integers.
    """
    return (
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
    )


@step
def load_step(
    duration: int,
    sleep_interval: float,
    input1: int,
    input2: int,
    input3: int,
    input4: int,
    input5: int,
    input6: int,
    input7: int,
    input8: int,
    input9: int,
    input10: int,
    input11: int,
    input12: int,
    input13: int,
    input14: int,
    input15: int,
    input16: int,
    input17: int,
    input18: int,
    input19: int,
    input20: int,
) -> Dict[str, Any]:
    """A step that performs API operations to stress test the ZenML server.

    This step will perform a number of API operations to stress test the ZenML server.
    It will list pipeline runs, stacks, stack components, and service connectors.

    Args:
        duration: The duration of the load test in seconds.
        sleep_interval: The interval to sleep between API calls in seconds.
        input1: The first input.
        input2: The second input.
        input3: The third input.
        input4: The fourth input.
        input5: The fifth input.
        input6: The sixth input.
        input7: The seventh input.
        input8: The eighth input.
        input9: The ninth input.
        input10: The tenth input.
        input11: The eleventh input.
        input12: The twelfth input.
        input13: The thirteenth input.
        input14: The fourteenth input.
        input15: The fifteenth input.
        input16: The sixteenth input.
        input17: The seventeenth input.
        input18: The eighteenth input.
        input19: The nineteenth input.
        input20: The twentieth input.

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
        p = client.list_pipeline_runs()
        if p.items:
            print("Fetching pipeline run...")
            client.get_pipeline_run(p.items[-1].id)
        print("Listing stacks...")
        s = client.list_stacks()
        if s.items:
            print("Fetching stack...")
            client.get_stack(s.items[-1].id)
        print("Listing stack components...")
        sc = client.list_stack_components()
        if sc.items:
            print("Fetching stack component...")
            client.get_stack_component(sc.items[-1].type, sc.items[-1].id)
        print("Listing service connectors...")
        sc = client.list_service_connectors()
        if sc.items:
            print("Fetching service connector...")
            client.get_service_connector(sc.items[-1].id)

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
    service_account_name="zenml-service-account",
    pod_settings=KubernetesPodSettings(
        resources={
            "requests": {"cpu": "100m", "memory": "800Mi"},
            # "limits": {"memory": "800Mi"}, # -> grows linearly with number of steps
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
        env=[
            {"name": "ZENML_LOGGING_VERBOSITY", "value": "debug"},
            {"name": "ZENML_ENABLE_RICH_TRACEBACK", "value": "false"},
        ],
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


@pipeline(enable_cache=False)
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
    result = init_step()

    after = []
    for i in range(num_parallel_steps):
        after.append(
            load_step(
                duration,
                sleep_interval,
                *result,
                id=f"load_step_{i}",
            )
        )

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
    default=1,
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
@click.option(
    "--max-parallel-steps",
    "-m",
    help="Maximum number of parallel steps to run",
    required=False,
    default=None,
    type=int,
)
@click.option(
    "--retries",
    "-r",
    help="Number of retries for the step",
    required=False,
    default=3,
    type=int,
)
def main(
    parallel_steps: int,
    duration: int,
    sleep_interval: float,
    num_tags: int,
    max_parallel_steps: Optional[int] = None,
    retries: int = 3,
) -> None:
    """Execute a ZenML load test with configurable parallel steps.

    This will spawn multiple parallel steps that continuously make API calls
    to stress test the ZenML server.

    Args:
        parallel_steps: The number of parallel steps to run.
        duration: The duration of the load test in seconds.
        sleep_interval: The interval to sleep between API calls in seconds.
        num_tags: The number of tags to add to the pipeline.
        max_parallel_steps: The maximum number of parallel steps to run.
        retries: The number of retries for the step.
    """
    if max_parallel_steps:
        click.echo(
            f"Starting load test with {parallel_steps} parallel steps with "
            f"max {max_parallel_steps} running steps at a time..."
        )
    else:
        click.echo(
            f"Starting load test with {parallel_steps} parallel steps..."
        )
    click.echo(f"Duration: {duration}s, Sleep Interval: {sleep_interval}s")

    kubernetes_settings = get_kubernetes_settings(max_parallel_steps)
    settings["orchestrator"] = kubernetes_settings

    load_test_pipeline.configure(
        tags=[Tag(name=f"tag_{i}", cascade=True) for i in range(num_tags)],
        settings=settings,
        retry=StepRetryConfig(max_retries=retries),
    )

    load_test_pipeline(
        num_parallel_steps=parallel_steps,
        duration=duration,
        sleep_interval=sleep_interval,
    )


if __name__ == "__main__":
    main()
