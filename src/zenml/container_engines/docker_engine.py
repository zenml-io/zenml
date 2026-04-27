#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Docker-backed :class:`ContainerEngine` implementation."""

import json
import re
import shutil
import subprocess
import tempfile
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    cast,
)

from docker.client import DockerClient
from docker.errors import DockerException

from zenml.constants import DOCKERHUB_REGISTRY_URI
from zenml.container_engines import ContainerEngine
from zenml.enums import ContainerEngineType
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.docker_settings import DockerBuildOptions
    from zenml.container_registries.base_container_registry import (
        BaseContainerRegistry,
    )
    from zenml.image_builders import BuildContext

logger = get_logger(__name__)


class DockerContainerEngine(ContainerEngine):
    """Container engine using the Docker CLI and/or docker-py."""

    def __init__(self) -> None:
        """Create a Docker engine (registry auth is per-operation)."""
        self._client: Optional[DockerClient] = None

    @property
    def engine_type(self) -> ContainerEngineType:
        """The type of the container engine.

        Returns:
            The type of the container engine.
        """
        return ContainerEngineType.DOCKER

    def check_availability(self) -> Tuple[bool, str | None]:
        """Check whether this engine is installed and accessible and return the error message if not.

        Returns:
            ``True`` if the engine binary and runtime are likely available, else
            ``False`` and an error message if not.
        """
        if not shutil.which("docker"):
            return (
                False,
                "`docker` is not installed or not accessible on your system.",
            )

        try:
            self.client.ping()
            return (True, None)
        except Exception:
            return (
                False,
                "Unable to connect to the Docker daemon. There are three "
                "common causes for this:\n"
                "1) The Docker daemon isn't running.\n"
                "2) The Docker client isn't configured correctly. The client "
                "loads its configuration from the following file: "
                "$HOME/.docker/config.json. If your configuration file is in a "
                "different location, set the `DOCKER_CONFIG` environment "
                "variable to the directory that contains your `config.json` "
                "file.\n"
                "3) If your Docker CLI is working fine but you ran into this "
                "issue, you might be using a non-default Docker context which "
                "is not supported by the Docker python library. To verify "
                "this, run `docker context ls` and check which context has a "
                "`*` next to it. If this is not the `default` context, copy "
                "the `DOCKER ENDPOINT` value of that context and set the "
                "`DOCKER_HOST` environment variable to that value.",
            )

    @property
    def client(self) -> DockerClient:
        """Return a docker-py client, reusing a cached unauthenticated instance.

        Returns:
            DockerClient: Connection to the local Docker daemon.

        Raises:
            RuntimeError: If docker-py cannot create a client from the
                environment (for example when the daemon is not running).
        """
        if self._client is not None:
            return self._client

        try:
            self._client = DockerClient.from_env()
        except DockerException as e:
            raise RuntimeError(
                "Could not create a Docker client from the environment. Is your "
                "Docker daemon running?"
            ) from e
        return self._client

    def login_client(
        self,
        username: str,
        password: str,
        registry: str,
    ) -> None:
        """Login to a Docker registry.

        Args:
            username: Registry username.
            password: Registry password or token.
            registry: Registry URI for login.

        Raises:
            AuthorizationException: If registry login fails.
        """
        try:
            self.client.login(
                username=username,
                password=password,
                registry=registry
                if registry != DOCKERHUB_REGISTRY_URI
                else None,
                reauth=True,
            )
        except DockerException as e:
            raise AuthorizationException(
                f"failed to authenticate with Docker registry {registry}: {e}"
            )

    @staticmethod
    def login_cli(
        username: str,
        password: str,
        registry: str,
    ) -> None:
        """Run ``docker login`` for the given registry.

        Args:
            username: Registry username.
            password: Registry password or token.
            registry: Registry host or URI.

        Raises:
            AuthorizationException: If ``docker login`` fails.
        """
        docker_login_cmd = [
            "docker",
            "login",
            "-u",
            username,
            "--password-stdin",
        ]
        if registry != DOCKERHUB_REGISTRY_URI:
            docker_login_cmd.append(registry)

        try:
            subprocess.run(
                docker_login_cmd,
                check=True,
                input=password.encode(),
            )
        except subprocess.CalledProcessError as e:
            raise AuthorizationException(
                f"Failed to authenticate to Docker registry '{registry}': {e}"
            ) from e

    @staticmethod
    def process_docker_stream(stream: Iterable[bytes]) -> List[Dict[str, Any]]:
        """Decode JSON lines from a docker-py build/push stream.

        Args:
            stream: Raw byte chunks from ``docker`` API ``build``/``push``.

        Raises:
            RuntimeError: If the stream contains an ``error`` payload.

        Returns:
            Auxiliary ``aux`` objects collected from the stream.
        """
        auxiliary_info = []

        for element in stream:
            lines = element.decode("utf-8").strip().split("\n")

            for line in lines:
                try:
                    line_json = json.loads(line)
                    if "error" in line_json:
                        raise RuntimeError(
                            f"Docker error: {line_json['error']}."
                        )
                    elif "stream" in line_json:
                        text = line_json["stream"].strip()
                        if "ERROR" in text:
                            logger.error(text)
                        elif re.match(r"^Step [0-9]+/[0-9]+", text):
                            logger.info(text)
                        else:
                            logger.debug(text)
                    elif "aux" in line_json:
                        auxiliary_info.append(line_json["aux"])
                except json.JSONDecodeError as error:
                    logger.warning(
                        "Failed to decode json for line '%s': %s", line, error
                    )

        return auxiliary_info

    def login(
        self,
        username: str,
        password: str,
        registry: str,
    ) -> None:
        """Authenticate the Docker client with the container registry credentials.

        Args:
            username: Registry username.
            password: Registry password or token.
            registry: Registry host or URI.
        """
        self.login_client(
            username=username,
            password=password,
            registry=registry,
        )
        self.login_cli(
            username=username,
            password=password,
            registry=registry,
        )

    def build(
        self,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Optional["DockerBuildOptions"] = None,
        container_registry: Optional["BaseContainerRegistry"] = None,
        **kwargs: Any,
    ) -> None:
        """Build an image using docker-py or ``docker build -``.

        Args:
            image_name: Target image reference including tag.
            build_context: Tarball context written to the Docker daemon.
            docker_build_options: Optional Docker build options.
            container_registry: When set, applies registry credentials for pulls.
            **kwargs: Additional keyword arguments.

        Returns:
            None
        """
        if container_registry:
            self.login_registry(container_registry)

        if kwargs.get("use_subprocess", False):
            self._build_cli(image_name, build_context, docker_build_options)
            return

        build_options = (
            docker_build_options.to_docker_python_sdk_options()
            if docker_build_options
            else {}
        )
        with tempfile.TemporaryFile(mode="w+b") as f:
            build_context.write_archive(f)
            f.seek(0)
            output_stream = self.client.images.client.api.build(
                fileobj=f,
                custom_context=True,
                tag=image_name,
                **build_options,
            )
        self.process_docker_stream(output_stream)

    def _build_cli(
        self,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Optional["DockerBuildOptions"] = None,
    ) -> None:
        """Run ``docker build`` with a tar context on stdin.

        Args:
            image_name: Target image reference including tag.
            build_context: Tarball context written to build stdin.
            docker_build_options: Optional Docker CLI build flags.

        Raises:
            RuntimeError: If ``docker build`` exits non-zero.
        """
        with tempfile.TemporaryFile(mode="w+b") as f:
            build_context.write_archive(f)
            f.seek(0)
            command = ["docker", "build", "-", "-t", image_name]
            if docker_build_options:
                command.extend(docker_build_options.to_docker_cli_options())
            process = subprocess.Popen(command, stdin=f)
            result = process.wait()
            if result != 0:
                raise RuntimeError(
                    f"Failed to build image {image_name} with `docker`. "
                    "Please check the logs above for more information."
                )

    def tag_image(self, source: str, target: str) -> None:
        """Apply a local tag using the Docker engine.

        Args:
            source: Existing image reference.
            target: Additional name:tag for the same image.
        """
        image = self.client.images.get(source)
        image.tag(target)

    def push_image(
        self,
        image_name: str,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> str:
        """Push an image and return a digest or image reference string.

        Args:
            image_name: Local image to push (must match registry URI).
            container_registry: Container registry to push to. Used for
                validation and credentials, if provided.

        Returns:
            Repository digest from docker-py when available; otherwise a
            string identity for the pushed image.

        Raises:
            RuntimeError: If push fails or the image digest is not found.
        """
        if (
            container_registry
            and container_registry.is_valid_image_name_for_registry(image_name)
        ):
            self.login_registry(container_registry)
            container_registry.prepare_image_push(image_name)

        logger.info("Pushing Docker image `%s`.", image_name)
        output_stream = self.client.images.push(image_name, stream=True)
        aux_info = self.process_docker_stream(output_stream)
        logger.info("Finished pushing Docker image.")

        image_name_without_tag, _ = image_name.rsplit(":", maxsplit=1)
        prefix_candidates = [f"{image_name_without_tag}@"]

        if image_name_without_tag.startswith(
            ("index.docker.io/", "docker.io/")
        ):
            image_name_without_index = image_name_without_tag.split(
                "/", maxsplit=1
            )[1]
            prefix_candidates.append(f"{image_name_without_index}@")

        image = self.client.images.get(image_name)
        repo_digests: List[str] = image.attrs["RepoDigests"]

        for digest in repo_digests:
            if digest.startswith(tuple(prefix_candidates)):
                return digest

        for info in reversed(aux_info):
            try:
                repo_digest = info["Digest"]
                return f"{image_name_without_tag}@{repo_digest}"
            except KeyError:
                pass
        raise RuntimeError(
            f"Unable to find repo digest after pushing image {image_name}."
        )

    def is_image_local(self, image_name: str) -> bool:
        """Return whether Docker considers the image local-only.

        Args:
            image_name: Image reference to inspect.

        Returns:
            ``True`` if the image is local without a resolved repo digest.
        """
        images = self.client.images.list(name=image_name)
        if not images:
            return False

        image = self.client.images.get(image_name)
        repo_digests = image.attrs["RepoDigests"]

        return len(repo_digests) == 0

    def get_image_repo_digest(
        self,
        image_name: str,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> Optional[str]:
        """Resolve a repository digest using docker-py (and registry creds).

        Args:
            image_name: Image reference to resolve.
            container_registry: When the name matches this registry, its
                credentials authenticate registry API access.

        Returns:
            Digest string when resolvable; ``None`` if not found or unknown.
        """
        if (
            container_registry
            and container_registry.is_valid_image_name_for_registry(image_name)
        ):
            self.login_registry(container_registry)

        try:
            metadata = self.client.images.get_registry_data(image_name)
        except Exception:
            return None

        return cast(str, metadata.id.split(":")[-1])

    def close(self) -> None:
        """Close the cached docker-py client if one was opened."""
        if self._client is not None:
            self._client.close()
            self._client = None
