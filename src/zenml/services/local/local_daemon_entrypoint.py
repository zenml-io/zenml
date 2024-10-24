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
"""Implementation of a local daemon entrypoint.

This executable file is utilized as an entrypoint for all ZenML services
that are implemented as locally running daemon processes.
"""

import os
from typing import cast

import click

from zenml.utils.daemon import daemonize

# Try to import the LocalZenServer here because it needs to be registered in the
# service registry early on in order to be available for use in other modules.
# If the LocalZenServer dependencies aren't installed, there is no need to register
# it anywhere so we simply pass.
try:
    from zenml.zen_server.deploy.daemon.daemon_zen_server import (  # noqa
        DaemonZenServer,
    )
except ImportError:
    pass


@click.command()
@click.option("--config-file", required=True, type=click.Path(exists=True))
@click.option("--log-file", required=False, type=click.Path())
@click.option("--pid-file", required=False, type=click.Path())
def run(
    config_file: str,
    log_file: str,
    pid_file: str,
) -> None:
    """Runs a ZenML service as a daemon process.

    Args:
        config_file: path to the configuration file for the service.
        log_file: path to the log file for the service.
        pid_file: path to the PID file for the service.
    """

    @daemonize(
        log_file=log_file, pid_file=pid_file, working_directory=os.getcwd()
    )
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
        from zenml.services import LocalDaemonService

        logger = get_logger(__name__)

        logger.info(
            "Loading service daemon configuration from %s", service_config_file
        )
        with open(service_config_file, "r") as f:
            config = f.read()

        integration_registry.activate_integrations()

        logger.debug("Running service daemon with configuration:\n %s", config)
        service = cast(
            "LocalDaemonService", LocalDaemonService.from_json(config)
        )
        if not isinstance(service, LocalDaemonService):
            raise TypeError(
                f"Expected service type LocalDaemonService but got "
                f"{type(service)} instead"
            )
        service.run()

    launch_service(config_file)


if __name__ == "__main__":
    run()
