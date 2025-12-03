from zenml import pipeline, step


@step(enable_cache=False)
def noop() -> None:
    pass


@pipeline(enable_cache=False)
def basic_pipeline():
    noop()


if __name__ == "__main__":
    basic_pipeline()
