import sys

from typing_extensions import Annotated

from zenml import pipeline, step


@step(enable_cache=False)
def register_artifact(step_id: int, run_id: int) -> Annotated[int, "artifact"]:
    return 100 * run_id + step_id


@pipeline
def parallel_(steps_count: int, run_id: int):
    for step_id in range(steps_count):
        register_artifact(step_id, run_id)


if __name__ == "__main__":
    run_prefix, i, steps_count = sys.argv[1:]
    parallel_.with_options(run_name=f"{run_prefix}_{i}")(steps_count, i)
