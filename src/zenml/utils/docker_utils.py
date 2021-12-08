import os
import tempfile
from typing import Dict, List, Optional

import pkg_resources

import docker
import zenml
from zenml.logger import get_logger

DEFAULT_BASE_IMAGE = f"zenmldocker/zenml:{zenml.__version__}"

logger = get_logger(__name__)


def create_dockerfile(
    base_image: str,
    command: Optional[str] = None,
    requirements: Optional[List[str]] = None,
    output_path: Optional[str] = None,
) -> str:
    """Creates a dockerfile.

    Args:
        base_image: The image to use as base for the dockerfile.
        command: The default command that gets executed when running a
            container of an image created by this dockerfile.
        requirements: Optional list of pip requirements to install.
        output_path: Path where the dockerfile should be written to.
            If this is not set, a filepath inside the temp directory will be
            used instead. **IMPORTANT**: Whoever uses this function is
            responsible for removing the created dockerfile.

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


def get_current_environment_requirements() -> Dict[str, str]:
    """Returns a dict of package requirements for the environment that
    the current python process is running in."""
    return {
        distribution.key: distribution.version
        for distribution in pkg_resources.working_set
    }


def build_docker_image(
    build_context_path: str,
    image_name: str,
    dockerfile_path: Optional[str] = None,
    requirements: Optional[List[str]] = None,
    use_local_requirements: bool = False,
    base_image: Optional[str] = None,
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
        base_image: The image to use as base for the docker image.
    """
    if not requirements and use_local_requirements:
        local_requirements = get_current_environment_requirements()
        requirements = [
            f"{package}=={version}"
            for package, version in local_requirements.items()
            if package != "zenml"  # exclude ZenML
        ]
        logger.info(
            "Using requirements from local environment to build "
            "docker image: %s",
            requirements,
        )

    temporary_dockerfile = not dockerfile_path
    if not dockerfile_path:
        dockerfile_path = create_dockerfile(
            requirements=requirements,
            base_image=base_image or DEFAULT_BASE_IMAGE,
        )

    logger.info(
        "Building docker image '%s', this might take a while...", image_name
    )
    try:
        docker_client = docker.from_env()
        docker_client.images.build(
            path=build_context_path,
            dockerfile=dockerfile_path,
            tag=image_name,
            pull=True,  # pull changes to base image
            rm=True,  # remove intermediate containers
        )
        logger.info("Finished building docker image.")
    finally:
        if temporary_dockerfile:
            logger.debug("Removing temporary dockerfile '%s'", dockerfile_path)
            os.remove(dockerfile_path)


def push_docker_image(image_name: str) -> None:
    """Pushes a docker image to a container registry.

    Args:
        image_name: The full name (including a tag) of the image to push.
    """
    logger.info("Pushing docker image '%s'.", image_name)
    docker_client = docker.from_env()
    docker_client.images.push(image_name)
    logger.info("Finished pushing docker image.")


def get_image_digest(image_name: str) -> Optional[str]:
    """Gets the digest of a docker image.

    Args:
        image_name: Name of the image to get the digest for.

    Returns:
        Returns the repo digest for the given image if there exists exactly one.
        If there are zero or multiple repo digests, returns `None`.
    """
    docker_client = docker.from_env()
    image = docker_client.images.get(image_name)
    repo_digests = image.attrs["RepoDigests"]
    if len(repo_digests) == 1:
        return repo_digests[0]
    else:
        logger.debug(
            "Found zero or more repo digests for docker image '%s': %s",
            image_name,
            repo_digests,
        )
        return None
