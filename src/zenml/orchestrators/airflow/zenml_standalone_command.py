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


class ZenStandaloneCommand(StandaloneCommand):
    """This class is an overwrite of the
    `airflow.cli.commands.standalone_command.StandaloneCommand`, with some of
    the code modifies from the original. Full credit to the original authors
    to create the original script."""

    def run(self) -> None:
        """Main run loop, mostly from the original Airflow"""
        self.print_output("standalone", "Starting Airflow Standalone")
        # Silence built-in logging at INFO
        logging.getLogger("").setLevel(logging.WARNING)
        # Startup checks and prep
        env = self.calculate_env()
        self.initialize_database()
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
                    self.print_ready()
                    shown_ready = True
                # Ensure we idle-sleep rather than fast-looping
                time.sleep(5)
            except KeyboardInterrupt:
                break
