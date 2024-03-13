from kfp import dsl
from kfp import compiler


@dsl.container_component(base_image="python:3.8")
def comp(message: str) -> str:
    print(message)
    return message


@dsl.pipeline
def my_pipeline(message: str) -> str:
    """My ML pipeline."""
    return comp(message=message).output


def _create_dynamic_component(
    image: str,
    command: list,
    arguments: list,
    component_name: str,
):
    @dsl.container_component
    def dynamic_component():
        dsl.ContainerSpec(
            image=image,
            command=command,
            args=arguments,
        )

    dynamic_component.__name__ = component_name
    return dynamic_component


compiler.Compiler().compile(my_pipeline, package_path="pipeline.yaml")
