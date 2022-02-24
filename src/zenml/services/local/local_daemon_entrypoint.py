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
"""
This executable file is utilized as an entrypoint for all ZenML services
that are implemented as locally running daemon processes.
"""

import os

import click

from zenml.utils.daemon import daemonize


@click.command()
@click.option("--config-file", required=True, type=click.Path(exists=True))
@click.option("--log-file", required=False, type=click.Path())
@click.option("--pid-file", required=False, type=click.Path())
def run(
    config_file: str,
    log_file: str,
    pid_file: str,
) -> None:
    @daemonize(
        log_file=log_file, pid_file=pid_file, working_directory=os.getcwd()
    )
    def launch_service(service_config_file: str) -> None:
        """Instantiate and launch a ZenML local service from its
        configuration file.
        """

        # doing zenml imports here to avoid polluting the stdout/sterr
        # with messages before daemonization is complete
        from zenml.integrations.registry import integration_registry
        from zenml.logger import get_logger
        from zenml.services import LocalDaemonService, ServiceRegistry

        logger = get_logger(__name__)

        logger.info(
            "Loading service daemon configuration from %s", service_config_file
        )
        with open(service_config_file, "r") as f:
            config = f.read()

        integration_registry.activate_integrations()

        logger.debug("Running service daemon with configuration:\n %s", config)
        service = ServiceRegistry().load_service_from_json(config)
        if not isinstance(service, LocalDaemonService):
            raise TypeError(
                f"Expected service type LocalDaemonService but got "
                f"{type(service)} instead"
            )
        service.run()

    launch_service(config_file)


if __name__ == "__main__":
    run()
