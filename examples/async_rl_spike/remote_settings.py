"""Docker image for the remote (Modal) run.

ZenML builds a single image for a dynamic pipeline (per-step images are not
built for dynamic pipelines, whose steps are only known at runtime), so the
orchestration container and every step share this one image. The steps run
on CPU (the GPU lives in the vLLM app), so torch is pinned to the CPU wheel
to keep the image small and its Modal import fast.
"""

import zenml
from zenml.config import DockerSettings
from zenml.integrations.modal.flavors.modal_sandbox_flavor import (
    ModalSandboxSettings,
)

# The scorer runs the generated ZenML pipeline inside the Modal sandbox, whose
# default image is a bare python without zenml. Boot it from the zenml image.
SANDBOX_SETTINGS = {
    "sandbox.modal": ModalSandboxSettings(
        image=f"zenmldocker/zenml:{zenml.__version__}-py3.12"
    )
}

# The local interpreter is 3.14, whose default ZenML parent image has no torch
# wheels. Pin the py3.12 ZenML image, which torch and friends still publish for.
FULL_DOCKER = DockerSettings(
    parent_image=f"zenmldocker/zenml:{zenml.__version__}-py3.12",
    requirements=[
        "torch==2.6.0+cpu",
        "trl==1.7.1",
        "transformers>=4.56,<5",
        "peft>=0.17,<1",
        "datasets>=3.0",
        "modal>=0.64",
    ],
    python_package_installer_args={
        "extra-index-url": "https://download.pytorch.org/whl/cpu",
        # uv defaults to first-index-wins, which mis-resolves shared packages
        # (e.g. importlib-metadata) from the torch index. Consider all indexes.
        "index-strategy": "unsafe-best-match",
    },
)

TRAINER_DOCKER = DockerSettings(
    parent_image=f"zenmldocker/zenml:{zenml.__version__}-py3.12",
    requirements=[
        "torch==2.6.0",
        "trl==1.7.1",
        "transformers>=4.56,<5",
        "peft>=0.17,<1",
        "datasets>=3.0",
        "modal>=0.64",
    ],
)
