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
import argparse

from zenml.entrypoints.step_entrypoint_configuration import (
    ENTRYPOINT_CONFIG_SOURCE_OPTION,
    StepEntrypointConfiguration,
)
from zenml.utils import source_utils


def main() -> None:
    """Runs the ZenML step defined by the command line arguments.

    This main logic for running the step is not implemented in this file,
    instead it simply creates an object of a
    `zenml.entrypoints.StepEntrypointConfiguration` subclass (the concrete
    implementation can be specified using the command line arguments) and calls
    its `run()` method.
    """
    # Read the source for the entrypoint configuration class from the command
    # line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(f"--{ENTRYPOINT_CONFIG_SOURCE_OPTION}", required=True)
    args, remaining_args = parser.parse_known_args()

    # Create an instance of the entrypoint configuration and pass it the
    # remaining command line arguments
    entrypoint_config_class = source_utils.load_source_path_class(
        args.entrypoint_config_source
    )
    if not issubclass(entrypoint_config_class, StepEntrypointConfiguration):
        raise TypeError(
            f"The entrypoint config source `{args.entrypoint_config_source}` "
            f"passed to the entrypoint is not pointing to a "
            f"`{StepEntrypointConfiguration}` subclass."
        )

    entrypoint_config = entrypoint_config_class(arguments=remaining_args)

    # Run the entrypoint configuration
    entrypoint_config.run()


if __name__ == "__main__":
    main()
