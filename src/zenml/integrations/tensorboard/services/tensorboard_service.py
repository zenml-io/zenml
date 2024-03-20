#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of the TensorBoard service."""

import uuid
from typing import Any, Dict, Union

from tensorboard import default, program  # type: ignore [import-untyped]
from tensorboard.uploader import (  # type: ignore [import-untyped]
    uploader_subcommand,
)

from zenml.logger import get_logger
from zenml.services import (
    HTTPEndpointHealthMonitor,
    HTTPEndpointHealthMonitorConfig,
    LocalDaemonService,
    LocalDaemonServiceConfig,
    LocalDaemonServiceEndpoint,
    LocalDaemonServiceEndpointConfig,
    ServiceEndpointProtocol,
    ServiceType,
)

logger = get_logger(__name__)


class TensorboardServiceConfig(LocalDaemonServiceConfig):
    """TensorBoard service configuration.

    Attributes:
        logdir: location of TensorBoard log files.
        max_reload_threads: the max number of threads that TensorBoard can use
            to reload runs. Each thread reloads one run at a time.
        reload_interval: how often the backend should load more data, in
            seconds. Set to 0 to load just once at startup.
    """

    logdir: str
    max_reload_threads: int = 1
    reload_interval: int = 5


class TensorboardService(LocalDaemonService):
    """TensorBoard service.

    This can be used to start a local TensorBoard server for one or more models.

    Attributes:
        SERVICE_TYPE: a service type descriptor with information describing
            the TensorBoard service class
        config: service configuration
        endpoint: optional service endpoint
    """

    SERVICE_TYPE = ServiceType(
        name="tensorboard",
        type="visualization",
        flavor="tensorboard",
        description="TensorBoard visualization service",
    )

    config: TensorboardServiceConfig
    endpoint: LocalDaemonServiceEndpoint

    def __init__(
        self,
        config: Union[TensorboardServiceConfig, Dict[str, Any]],
        **attrs: Any,
    ) -> None:
        """Initialization for TensorBoard service.

        Args:
            config: service configuration
            **attrs: additional attributes
        """
        # ensure that the endpoint is created before the service is initialized
        # TODO [ENG-697]: implement a service factory or builder for TensorBoard
        #   deployment services
        if (
            isinstance(config, TensorboardServiceConfig)
            and "endpoint" not in attrs
        ):
            endpoint = LocalDaemonServiceEndpoint(
                config=LocalDaemonServiceEndpointConfig(
                    protocol=ServiceEndpointProtocol.HTTP,
                ),
                monitor=HTTPEndpointHealthMonitor(
                    config=HTTPEndpointHealthMonitorConfig(
                        healthcheck_uri_path="",
                        use_head_request=True,
                    )
                ),
            )
            attrs["endpoint"] = endpoint
        super().__init__(config=config, uuid=uuid.uuid4(), **attrs)

    def run(self) -> None:
        """Initialize and run the TensorBoard server."""
        logger.info(
            "Starting TensorBoard service as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()

        try:
            tensorboard = program.TensorBoard(
                plugins=default.get_plugins(),
                subcommands=[uploader_subcommand.UploaderSubcommand()],
            )
            tensorboard.configure(
                logdir=self.config.logdir,
                port=self.endpoint.status.port,
                host="localhost",
                max_reload_threads=self.config.max_reload_threads,
                reload_interval=self.config.reload_interval,
            )
            tensorboard.main()
        except KeyboardInterrupt:
            logger.info(
                "TensorBoard service stopped. Resuming normal execution."
            )
