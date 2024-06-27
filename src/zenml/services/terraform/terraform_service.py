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
"""Implementation of a Terraform ZenML service."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Tuple

import python_terraform
from pydantic import Field

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.services.container.container_service import SERVICE_LOG_FILE_NAME
from zenml.services.service import BaseService, ServiceConfig
from zenml.services.service_status import ServiceState, ServiceStatus
from zenml.utils.io_utils import copy_dir, create_dir_recursive_if_not_exists

logger = get_logger(__name__)


SERVICE_CONFIG_FILE_NAME = "service.json"
SERVICE_CONTAINER_GLOBAL_CONFIG_DIR = "zenconfig"
SERVICE_CONTAINER_GLOBAL_CONFIG_PATH = os.path.join(
    "/", SERVICE_CONTAINER_GLOBAL_CONFIG_DIR
)


class TerraformServiceConfig(ServiceConfig):
    """Terraform service configuration.

    Attributes:
        root_runtime_path: the root path where the service stores its files.
        singleton: set to True to store the service files directly in the
            `root_runtime_path` directory instead of creating a subdirectory for
            each service instance. Only has effect if the `root_runtime_path` is
            also set.
        directory_path: the path to the directory that hosts all the HCL files.
        copy_terraform_files: whether to copy the HCL files to the service
            runtime directory.
        log_level: the log level to set the terraform client to. Choose one of
            TRACE, DEBUG, INFO, WARN or ERROR (case insensitive).
        variables_file_path: the path to the file that stores all variable values.
    """

    root_runtime_path: str
    singleton: bool = False
    directory_path: str
    copy_terraform_files: bool = False
    log_level: str = "ERROR"
    variables_file_path: str = "values.tfvars.json"


class TerraformServiceStatus(ServiceStatus):
    """Terraform service status.

    Attributes:
        runtime_path: the path where the service files (e.g. the configuration
            file used to start the service daemon and the logfile) are located
    """

    runtime_path: Optional[str] = None

    @property
    def config_file(self) -> Optional[str]:
        """Get the path to the service configuration file.

        Returns:
            The path to the configuration file, or None, if the
            service has never been started before.
        """
        if not self.runtime_path:
            return None
        return os.path.join(self.runtime_path, SERVICE_CONFIG_FILE_NAME)

    @property
    def log_file(self) -> Optional[str]:
        """Get the path to the log file where the service output is/has been logged.

        Returns:
            The path to the log file, or None, if the service has never been
            started before.
        """
        if not self.runtime_path:
            return None
        return os.path.join(self.runtime_path, SERVICE_LOG_FILE_NAME)


class TerraformService(BaseService):
    """A service represented by a set of resources deployed using a terraform recipe.

    This class extends the base service class with functionality concerning
    the life-cycle management and tracking of external services managed using
    terraform recipes.


    Attributes:
        config: service configuration
        status: service status
    """

    config: TerraformServiceConfig
    status: TerraformServiceStatus = Field(
        default_factory=TerraformServiceStatus
    )

    _terraform_client: Optional[python_terraform.Terraform] = None

    @property
    def terraform_client(self) -> python_terraform.Terraform:
        """Initialize and/or return the terraform client.

        Returns:
            The terraform client.
        """
        if self._terraform_client is None:
            working_dir = self.config.directory_path
            if self.config.copy_terraform_files:
                assert self.status.runtime_path is not None
                working_dir = self.status.runtime_path
            self._terraform_client = python_terraform.Terraform(
                working_dir=working_dir,
            )
        return self._terraform_client

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the external service.

        If the final output name provided in the config exists as a non-null value,
        then it's reasonable to assume that the service is up and running.

        Returns:
            The operational state of the external service and a message
            providing additional information about that state (e.g. a
            description of the error if one is encountered while checking the
            service status).
        """
        code, out, err = self.terraform_client.plan(
            detailed_exitcode=True,
            refresh=False,
            var=self.get_vars(),
            input=False,
            raise_on_error=False,
        )

        if code == 0:
            return (ServiceState.ACTIVE, "The deployment is active.")
        elif code == 2:
            return (
                ServiceState.INACTIVE,
                "The deployment isn't active or needs an update.",
            )
        else:
            return (ServiceState.ERROR, f"Deployment error: \n{err}")

    def _update_service_config(self) -> None:
        """Update the service configuration file.

        This function is called after the service has been started, to update
        the service configuration file with the runtime path of the service.
        """
        # write the service information in the service config file
        assert self.status.config_file is not None

        with open(self.status.config_file, "w") as f:
            f.write(self.model_dump_json(indent=4))

    def _write_vars_to_file(self, vars: Dict[str, Any]) -> None:
        """Write variables to the variables file.

        Args:
            vars: The variables to write to the file.
        """
        import json

        path = self.terraform_client.working_dir
        variables_file_path = os.path.join(
            path, self.config.variables_file_path
        )
        with open(variables_file_path, "w") as f:
            json.dump(vars, f)

    def _init_and_apply(self) -> None:
        """Function to call terraform init and terraform apply.

        The init call is not repeated if any successful execution has
        happened already, to save time.

        Raises:
            RuntimeError: if init or apply function fails.
        """
        self._update_service_config()

        # this directory gets created after a successful init
        previous_run_dir = os.path.join(
            self.terraform_client.working_dir, ".ignoreme"
        )
        if fileio.exists(previous_run_dir):
            logger.info(
                "Terraform already initialized, "
                "terraform init will not be executed."
            )
        else:
            ret_code, _, _ = self.terraform_client.init(capture_output=False)
            if ret_code != 0:
                raise RuntimeError("The command 'terraform init' failed.")
            fileio.mkdir(previous_run_dir)

        # get variables from the recipe as a python dictionary
        vars = self.get_vars()

        # once init is successful, call terraform apply
        self.terraform_client.apply(
            var=vars,
            input=False,
            capture_output=False,
            raise_on_error=True,
            refresh=False,
        )

        # write variables to the variable file after execution is successful
        self._write_vars_to_file(vars)

    def get_vars(self) -> Dict[str, Any]:
        """Get variables as a dictionary from values.tfvars.json.

        Returns:
            A dictionary of variables to use for the stack recipes
            derived from the tfvars.json file.

        Raises:
            FileNotFoundError: if the values.tfvars.json file is not
                found in the stack recipe.
            TypeError: if the file doesn't contain a dictionary of variables.
        """
        import json

        path = self.terraform_client.working_dir
        variables_file_path = os.path.join(
            path, self.config.variables_file_path
        )
        if not fileio.exists(variables_file_path):
            raise FileNotFoundError(
                "The file values.tfvars.json was not found in the "
                f"recipe's directory at {variables_file_path}. Please "
                "verify if it exists."
            )

        # read values into a dict and return
        with fileio.open(variables_file_path, "r") as f:
            variables = json.load(f)
        if not isinstance(variables, dict):
            raise TypeError(
                "The values.tfvars.json file must contain a dictionary "
                "of variables."
            )
        return variables

    def _destroy(self) -> None:
        """Function to call terraform destroy on the given path."""
        # get variables from the recipe as a python dictionary
        vars = self.get_vars()

        self.terraform_client.destroy(
            var=vars,
            capture_output=False,
            raise_on_error=True,
            force=python_terraform.IsNotFlagged,
            refresh=False,
        )

        # set empty vars to the file

    def _setup_runtime_path(self) -> None:
        """Set up the runtime path for the service.

        This method sets up the runtime path for the service.
        """
        # reuse the config file and logfile location from a previous run,
        # if available
        copy_terraform_files = True
        if not self.status.runtime_path or not os.path.exists(
            self.status.runtime_path
        ):
            if self.config.root_runtime_path:
                if self.config.singleton:
                    self.status.runtime_path = self.config.root_runtime_path
                else:
                    self.status.runtime_path = os.path.join(
                        self.config.root_runtime_path,
                        str(self.uuid),
                    )
                if fileio.isdir(self.status.runtime_path):
                    copy_terraform_files = False
                else:
                    create_dir_recursive_if_not_exists(
                        str(self.status.runtime_path)
                    )
            else:
                self.status.runtime_path = tempfile.mkdtemp(
                    prefix="zenml-service-"
                )

            if copy_terraform_files and self.config.copy_terraform_files:
                copy_dir(
                    self.config.directory_path,
                    self.status.runtime_path,
                )

    def provision(self) -> None:
        """Provision the service."""
        self._setup_runtime_path()
        self.check_installation()
        self._set_log_level()
        self._init_and_apply()

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the service.

        Args:
            force: if True, the service will be deprovisioned even if it is
                in a failed state.
        """
        self.check_installation()
        self._set_log_level()
        self._destroy()
        # in case of singleton services, this will remove the config
        # path as a whole and otherwise, this removes the specific UUID
        # directory
        assert self.status.config_file is not None
        shutil.rmtree(Path(self.status.config_file).parent)

    # overwriting the start/stop function to remove the progress indicator
    # having which doesn't allow tf logs to be shown in stdout
    def start(self, timeout: int = 0) -> None:
        """Start the service and optionally wait for it to become active.

        Args:
            timeout: amount of time to wait for the service to become active.
                If set to 0, the method will return immediately after checking
                the service status.
        """
        self.admin_state = ServiceState.ACTIVE
        self.provision()

    def stop(self, timeout: int = 0, force: bool = False) -> None:
        """Stop the service and optionally wait for it to shutdown.

        Args:
            timeout: amount of time to wait for the service to shutdown.
                If set to 0, the method will return immediately after checking
                the service status.
            force: if True, the service will be forcefully stopped.
        """
        self.admin_state = ServiceState.INACTIVE
        self.deprovision()

    def get_logs(
        self, follow: bool = False, tail: Optional[int] = None
    ) -> Generator[str, bool, None]:
        """Retrieve the service logs.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Raises:
            NotImplementedError: not implemented.
        """
        raise NotImplementedError(
            "This method is not available for Terraform services."
        )

    def get_outputs(self, output: Optional[str] = None) -> Dict[str, Any]:
        """Get outputs from the terraform state.

        Args:
            output: if specified, only the output with the given name will be
                returned. Otherwise, all outputs will be returned.

        Returns:
            A dictionary of outputs from the terraform state.
        """
        if output:
            # if output is specified, then full_outputs is just a string
            full_outputs = self.terraform_client.output(
                output, full_value=True
            )
            return {output: full_outputs}
        else:
            # get value of the "value" key in the value of full_outputs
            # and assign it to the key in the output dict
            full_outputs = self.terraform_client.output(full_value=True)
            outputs = {k: v["value"] for k, v in full_outputs.items()}
            return outputs

    def check_installation(self) -> None:
        """Checks if necessary tools are installed on the host system.

        Raises:
            RuntimeError: if any required tool is not installed.
        """
        if not self._is_terraform_installed():
            raise RuntimeError(
                "Terraform is required for stack recipes to run and was not "
                "found installed on your machine or not available on  "
                "your $PATH. Please visit "
                "https://learn.hashicorp.com/tutorials/terraform/install-cli "
                "to install it."
            )

    def _is_terraform_installed(self) -> bool:
        """Checks if terraform is installed on the host system.

        Returns:
            True if terraform is installed, false otherwise.
        """
        # check terraform version to verify installation.
        try:
            self.terraform_client.cmd("-version")
        except FileNotFoundError:
            return False

        return True

    def _set_log_level(self) -> None:
        """Set TF_LOG env var to the log_level provided by the user."""
        os.environ["TF_LOG"] = self.config.log_level
