#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import logging
import time

from airflow.cli.commands.standalone_command import (
    StandaloneCommand,
    SubCommand,
)


class AirflowCommander(StandaloneCommand):
    """This class is an overwrite of the
    `airflow.cli.commands.standalone_command.StandaloneCommand`, with some of
    the code modifies from the original. Full credit to the original authors
    to create the original script."""

    def _silence_logging(self) -> int:
        """Silences logging.

        Returns:
            Returns the old default level.
        """
        # Silence built-in logging at INFO
        old_level = logging.getLogger("").level
        logging.getLogger("").setLevel(logging.WARNING)
        return old_level

    def _unsilence_logging(self, level: int = logging.INFO) -> None:
        """Silences logging.

        Args:
            level: The level at which to unsilence logging.
        """
        # Reverts to new_level
        logging.getLogger("").setLevel(level)

    def up(self) -> None:
        """Ups the airflow scheduler, webserver, and triggerer."""
        self.print_output("zenml_airflow", "Starting Airflow components..")

        old_level = self._silence_logging()
        env = self.calculate_env()
        # Set up commands to run
        self.subcommands["scheduler"] = SubCommand(
            self,
            name="scheduler",
            command=["scheduler"],
            env=env,
        )
        self.subcommands["webserver"] = SubCommand(
            self,
            name="webserver",
            command=["webserver", "--port", "8080"],
            env=env,
        )
        self.subcommands["triggerer"] = SubCommand(
            self,
            name="triggerer",
            command=["triggerer"],
            env=env,
        )
        # Run subcommand threads
        for command in self.subcommands.values():
            command.start()

        # Run output loop
        shown_ready = False
        while not shown_ready:
            try:
                # Print all the current lines onto the screen
                self.update_output()
                # Print info banner when all components are ready and the
                # delay has passed
                if not self.ready_time and self.is_ready():
                    self.ready_time = time.monotonic()
                if (
                    not shown_ready
                    and self.ready_time
                    and time.monotonic() - self.ready_time > self.ready_delay
                ):
                    shown_ready = True
                # Ensure we idle-sleep rather than fast-looping
                time.sleep(1)
            except KeyboardInterrupt:
                break
        self._unsilence_logging(old_level)

    def down(self) -> None:
        """Stops all open threads."""
        self.print_output("zenml_airflow", "Shutting down components..")
        for command in self.subcommands.values():
            command.stop()
        for command in self.subcommands.values():
            command.join()
        self.print_output("zenml_airflow", "Shut down complete.")

    def bootstrap(self) -> None:
        """Main run loop, mostly from the original Airflow codebase."""
        old_level = self._silence_logging()
        self.print_output("zenml_airflow", "Bootstrapping Airflow..")
        # Startup checks and prep
        self.calculate_env()
        self.initialize_database()
        self._unsilence_logging(old_level)
