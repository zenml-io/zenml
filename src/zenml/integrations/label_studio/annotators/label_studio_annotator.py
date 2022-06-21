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

import os
import subprocess
import sys
from typing import ClassVar

from zenml.exceptions import ProvisioningError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils, networking_utils

logger = get_logger(__name__)

import sys
from typing import Any, ClassVar, List

from zenml.annotators.base_annotator import BaseAnnotator
from zenml.integrations.label_studio import LABEL_STUDIO_ANNOTATOR_FLAVOR

DEFAULT_LABEL_STUDIO_PORT = 8093


class LabelStudioAnnotator(BaseAnnotator):
    """Class to interact with the Label Studio annotation interface."""

    port: int = DEFAULT_LABEL_STUDIO_PORT

    FLAVOR: ClassVar[str] = LABEL_STUDIO_ANNOTATOR_FLAVOR

    def get_url(self) -> str:
        """Gets the URL of the annotation interface."""
        return "https://labelstudio.org"

    def get_datasets(self) -> List[str]:
        """Gets the datasets currently available for annotation."""

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory.

        Returns:
            Path to the root directory.
        """
        return os.path.join(
            io_utils.get_global_config_directory(),
            "annotators",
            str(self.uuid),
        )

    @property
    def _pid_file_path(self) -> str:
        """Returns path to the daemon PID file.

        Returns:
            Path to the daemon PID file.
        """
        return os.path.join(self.root_directory, "label_studio_daemon.pid")

    @property
    def _log_file(self) -> str:
        """Path of the daemon log file.

        Returns:
            Path to the daemon log file.
        """
        return os.path.join(self.root_directory, "label_studio_daemon.log")

    @property
    def is_provisioned(self) -> bool:
        """If the component provisioned resources to run locally.

        Returns:
            True if the component provisioned resources to run locally.
        """
        return fileio.exists(self.root_directory)

    @property
    def is_running(self) -> bool:
        """If the component is running locally.

        Returns:
            True if the component is running locally, False otherwise.
        """
        if sys.platform != "win32":
            from zenml.utils.daemon import check_if_daemon_is_running

            if not check_if_daemon_is_running(self._pid_file_path):
                return False
        else:
            # Daemon functionality is not supported on Windows, so the PID
            # file won't exist. This if clause exists just for mypy to not
            # complain about missing functions
            pass

        return True

    def provision(self) -> None:
        """Spins up the annotation server backend."""
        fileio.makedirs(self.root_directory)

    def deprovision(self) -> None:
        """Spins down the annotation server backend."""
        if fileio.exists(self._log_file):
            fileio.remove(self._log_file)

    def resume(self) -> None:
        """Resumes the annotation interface."""
        if self.is_running:
            logger.info("Local kubeflow pipelines deployment already running.")
            return

        self.start_annotator_daemon()

    def suspend(self) -> None:
        """Suspends the annotation interface."""
        if not self.is_running:
            logger.info("Local annotation server is not running.")
            return

        self.stop_annotator_daemon()

    def start_annotator_daemon(self) -> None:
        """Starts the annotation server backend."""
        command = [
            "label-studio",
            "start",
            "--no-browser",
            "--port",
            f"{self.port}",
        ]

        if sys.platform == "win32":
            logger.warning(
                "Daemon functionality not supported on Windows. "
                "In order to access the Label Studio server locally, "
                "please run '%s' in a separate command line shell.",
                self.port,
                " ".join(command),
            )
        elif not networking_utils.port_available(self.port):
            raise ProvisioningError(
                f"Unable to port-forward Label Studio to local "
                f"port {self.port} because the port is occupied. In order to "
                f"access Label Studio locally, please "
                f"change the configuration to use an available "
                f"port or stop the other process currently using the port."
            )
        else:
            from zenml.utils import daemon

            def _daemon_function() -> None:
                """Forwards the port of the Kubeflow Pipelines Metadata pod ."""
                subprocess.check_call(command)

            daemon.run_as_daemon(
                _daemon_function,
                pid_file=self._pid_file_path,
                log_file=self._log_file,
            )
            logger.info(
                "Started Label Studio daemon (check the daemon"
                "logs at `%s` in case you're not able to access the annotation "
                "interface).",
                self._log_file,
            )

    def stop_annotator_daemon(self) -> None:
        """Stops the annotation server backend."""
        if fileio.exists(self._pid_file_path):
            if sys.platform == "win32":
                # Daemon functionality is not supported on Windows, so the PID
                # file won't exist. This if clause exists just for mypy to not
                # complain about missing functions
                pass
            else:
                from zenml.utils import daemon

                daemon.stop_daemon(self._pid_file_path)
                fileio.remove(self._pid_file_path)

    def launch(self) -> None:
        """Launches the annotation interface."""
        # Define the URL where Label Studio is accessible and the API key for your user account
        LABEL_STUDIO_URL = "http://localhost:8080"
        API_KEY = "872ce7506559e64571991b4053255c99bd71f76a"

        # Import the SDK and the client module
        from label_studio_sdk import Client

        # Connect to the Label Studio API and check the connection
        ls = Client(url=LABEL_STUDIO_URL, api_key=API_KEY)
        ls.check_connection()

    def add_dataset(self, dataset_name: str) -> None:
        """Registers a dataset for annotation."""

    def delete_dataset(self, dataset_name: str) -> None:
        """Deletes a dataset from the annotation interface."""

    def get_dataset(self, dataset_name: str) -> None:
        """Gets the dataset with the given name."""

    def get_annotations(self, dataset_name: str) -> None:
        """Gets the annotations for the given dataset."""

    def tag_dataset(self, dataset_name: str, tag: str) -> None:
        """Tags the dataset with the given name with the given tag."""

    def untag_dataset(self, dataset_name: str, tag: str) -> None:
        """Untags the dataset with the given name with the given tag."""

    def get_labeled_data(self, dataset_name: str) -> None:
        """Gets the labeled data for the given dataset."""

    def get_unlabeled_data(self, dataset_name: str) -> None:
        """Gets the unlabeled data for the given dataset."""

    def export_data(self, identifier: str, export_config) -> Any:
        """Exports the data for the given identifier."""

    def import_data(self, identifier: str, import_config) -> None:
        """Imports the data for the given identifier."""
