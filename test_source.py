from zenml import step, pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(source_files="download")


@step
def step1() -> int:
    return 1


@pipeline(settings={"docker": docker_settings})
def my_pipeline():
    step1()


if __name__ == "__main__":
    my_pipeline()
