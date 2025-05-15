"""This pipeline is used to test the different sorting mechanisms."""

from zenml import pipeline, step 


@step
def basic_step() -> str:
    """Step to return a string."""
    return "Hello, World!"


@pipeline(enable_cache=False)
def basic_pipeline():
    """Pipeline with tags."""
    basic_step()


if __name__ == "__main__":
    basic_pipeline()
