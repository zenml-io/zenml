from pathlib import Path

import zenml
from zenml import pipeline, step
from zenml.config import DockerSettings
from zenml.config.resource_settings import ResourceSettings
from zenml.integrations.modal.flavors.modal_step_operator_flavor import (
    ModalStepOperatorSettings,
)
from zenml.integrations.constants import PYTORCH, EVIDENTLY



zenml_git_root = Path(zenml.__file__).parents[2]

docker_settings = DockerSettings(
    dockerfile=str(zenml_git_root / "docker" / "zenml-dev.Dockerfile"),
    build_context_root=str(zenml_git_root),
    python_package_installer="uv",
    required_integrations=[PYTORCH, EVIDENTLY],
    # prevent_build_reuse=True,
)

modal_resource_settings = ResourceSettings(cpu_count=1.25, gpu_count=1)

modal_settings = ModalStepOperatorSettings(gpu="H100")


@step
def hello_world() -> int:
    print("Hello world!")
    return 3


@step(
    step_operator="modal",
    settings={
        "step_operator.modal": modal_settings,
        "resources": modal_resource_settings,
    },
)
def hello_world_on_modal(some_number: int) -> int:
    manipulated_number = some_number * 3
    print(f"Hello I'm inside a container! {manipulated_number}")
    return manipulated_number


@step
def final_step(some_manipulated_number: int) -> None:
    print(f"Final number: {some_manipulated_number}")


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def hello_world_pipeline():
    some_val = hello_world()
    manipulated_number = hello_world_on_modal(some_val)
    final_step(manipulated_number)


if __name__ == "__main__":
    hello_world_pipeline()
