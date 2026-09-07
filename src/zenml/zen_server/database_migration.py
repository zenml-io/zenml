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
"""Database migration entry point for ZenML server deployments."""

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StoreType
from zenml.logger import get_logger
from zenml.zen_server.otel import configure_otel, otel_span, shutdown_otel
from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)


def main() -> None:
    """Initialize and migrate the ZenML server database."""
    store_config = GlobalConfiguration().store_configuration
    if store_config.type != StoreType.SQL:
        logger.warning("Database migration requires a SQL store.")
        return

    try:
        configure_otel()
        with otel_span("zenml.database.migrate"):
            BaseZenStore.create_store(store_config)
        logger.info("Database migration finished.")
    finally:
        shutdown_otel()


if __name__ == "__main__":
    main()
