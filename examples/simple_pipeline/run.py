"""Run a minimal ZenML pipeline."""

from zenml import pipeline, step


@step
def greet(name: str) -> str:
    """Create a greeting artifact for ``name``."""
    message = f"Hello, {name}!"
    print(message)
    return message


@pipeline
def simple_pipeline(name: str = "ZenML") -> str:
    """Run one step and return its output artifact."""
    return greet(name)


def main() -> None:
    """Execute the example pipeline."""
    run = simple_pipeline.with_options(run_name="simple_pipeline_demo")()
    print(f"Pipeline run {run.id} finished with status: {run.status}")


if __name__ == "__main__":
    main()
