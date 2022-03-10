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
import subprocess
from pathlib import Path

from zenml.enums import StorageType
from zenml.io.utils import get_global_config_directory
from zenml.stack_stores import BaseStackStore, SqlStackStore


class Service:
    """ZenML service class."""

    def __init__(
        self, storage_type: StorageType = StorageType.SQLITE_STORAGE
    ) -> None:

        """Initialize a service instance.

        Args:
            storage_type: Optionally specify how to persist stacks. Valid
                options: SQLITE_STORAGE, YAML_STORAGE
        """
        self.stack_store: BaseStackStore
        self.root: Path = Path(get_global_config_directory())
        if storage_type == StorageType.SQLITE_STORAGE:
            self.stack_store = SqlStackStore(
                f"sqlite:///{self.root / 'service_stack_store.db'}"
            )

    def run(self) -> None:
        """Run the service in a foreground process"""
        # TODO: make async
        # try:
        subprocess.check_call(["uvicorn", "zenml.zervice:app", "--reload"])
        # TODO: don't just call the uvicorn --reload subprocess!
        # except KeyboardInterrupt:
        #     print("shutting down server")
