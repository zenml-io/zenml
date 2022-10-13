#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of a containerized service entrypoint.

This executable file is utilized as an entrypoint for all ZenML services
that are implemented as locally running docker containers.
"""

import os
import sys

import click

from zenml.services.container.container_service import (
    SERVICE_CONTAINER_PATH,
    SERVICE_LOG_FILE_NAME,
)

# Try to import the DockerZenServer here because it needs to be registered in the
# service registry early on in order to be available for use in other modules.
try:
    from zenml.zen_server.deploy.docker.docker_zen_server import (  # noqa
        DockerZenServer,
    )
except ImportError:
    pass


def launch_service(service_config_file: str) -> None:
    """Instantiate and launch a ZenML local service from its configuration file.

    Args:
        service_config_file: the path to the service configuration file.

    Raises:
        TypeError: if the service configuration file is the wrong type.
    """
    # doing zenml imports here to avoid polluting the stdout/stderr
    # with messages before daemonization is complete
    from zenml.integrations.registry import integration_registry
    from zenml.logger import get_logger
    from zenml.services import ContainerService, ServiceRegistry

    logger = get_logger(__name__)

    logger.info("Loading service configuration from %s", service_config_file)
    with open(service_config_file, "r") as f:
        config = f.read()

    integration_registry.activate_integrations()

    logger.debug(
        "Running containerized service with configuration:\n %s", config
    )
    service = ServiceRegistry().load_service_from_json(config)
    if not isinstance(service, ContainerService):
        raise TypeError(
            f"Expected service type ContainerService but got "
            f"{type(service)} instead"
        )
    service.run()


@click.command()
@click.option("--config-file", required=True, type=click.Path(exists=True))
def run(
    config_file: str,
) -> None:
    """Runs a ZenML service as a docker container.

    Args:
        config_file: path to the configuration file for the service.
    """
    log_file = os.path.join(SERVICE_CONTAINER_PATH, SERVICE_LOG_FILE_NAME)

    devnull = "/dev/null"
    if hasattr(os, "devnull"):
        devnull = os.devnull

    devnull_fd = os.open(devnull, os.O_RDWR)
    log_fd = os.open(log_file, os.O_CREAT | os.O_RDWR | os.O_APPEND)
    out_fd = log_fd or devnull_fd

    os.dup2(devnull_fd, sys.stdin.fileno())
    os.dup2(out_fd, sys.stdout.fileno())
    os.dup2(out_fd, sys.stderr.fileno())

    launch_service(config_file)


if __name__ == "__main__":
    run()
