import os
import tempfile
from typing import List, Optional

import pkg_resources

import docker
import zenml
from zenml.logger import get_logger

DEFAULT_BASE_IMAGE = f"zenmldocker/zenml:{zenml.__version__}"

logger = get_logger(__name__)


def create_dockerfile(
    command: Optional[str] = None,
    requirements: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    base_image: str = DEFAULT_BASE_IMAGE,
) -> str:
    """Creates a dockerfile.

    Args:
        command: The default command that gets executed when running a
            container of an image created by this dockerfile.
        requirements: Optional list of pip requirements to install.
        output_path: Path where the dockerfile should be written to.
            If this is not set, a filepath inside the temp directory will be
            used instead. **IMPORTANT**: Whoever uses this function is
            responsible for removing the created dockerfile.
        base_image: The image to use as base for the dockerfile.

    Returns:
        A path to the dockerfile.
    """
    lines = [f"FROM {base_image}", "WORKDIR /app"]

    if requirements:
        lines.extend(
            [
                f"RUN pip install --no-cache {' '.join(requirements)}",
            ]
        )

    lines.append("COPY . .")

    if command:
        lines.append(f"CMD {command}")

    if not output_path:
        _, output_path = tempfile.mkstemp()

    logger.debug("Writing dockerfile to path '%s'", output_path)
    with open(output_path, "w") as output_file:
        output_file.write("\n".join(lines))

    return output_path


def get_current_environment_requirements() -> List[str]:
    """Returns a list of package requirements for the environment that
    the current python process is running in."""
    return [
        f"{distribution.key}=={distribution.version}"
        for distribution in pkg_resources.working_set
    ]


def build_docker_image(
    build_context_path: str,
    image_name: str,
    dockerfile_path: Optional[str] = None,
    requirements: Optional[List[str]] = None,
    use_local_requirements: bool = False,
) -> None:
    """Builds a docker image.

    Args:
        build_context_path: Path to a directory that will be sent to the
            docker daemon as build context.
        image_name: The name to use for the created docker image.
        dockerfile_path: Optional path to a dockerfile. If no value is given,
            a temporary dockerfile will be created.
        requirements: Optional list of pip requirements to install. This
            will only be used if no value is given for `dockerfile_path`.
        use_local_requirements: If `True` and no values are given for
            `dockerfile_path` and `requirements`, then the packages installed
            in the environment of the current python processed will be
            installed in the docker image.
    """
    if not requirements and use_local_requirements:
        requirements = get_current_environment_requirements()
        logger.info(
            "Using requirements from local environment to build "
            "docker image: %s",
            requirements,
        )

    temporary_dockerfile = not dockerfile_path
    if not dockerfile_path:
        dockerfile_path = create_dockerfile(requirements=requirements)

    logger.info(
        "Building docker image '%s', this might take a while...", image_name
    )
    docker_client = docker.from_env()
    docker_client.images.build(
        path=build_context_path,
        dockerfile=dockerfile_path,
        tag=image_name,
        rm=True,  # remove intermediate containers
    )
    logger.info("Finished building docker image.")

    if temporary_dockerfile:
        logger.debug("Removing temporary dockerfile '%s'", dockerfile_path)
        os.remove(dockerfile_path)
