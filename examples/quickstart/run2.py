from zenml import pipeline, step

# Write a simple pipeline


@step
def simple_step() -> int:
    return 1


@step
def simple_step_2(a: int) -> str:
    return "wow"


@pipeline
def my_pipeline():
    a = simple_step()
    _ = simple_step_2(a)


if __name__ == "__main__":
    my_pipeline()
