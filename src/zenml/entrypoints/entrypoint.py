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
"""Functionality to run ZenML steps or pipelines."""

import argparse
import logging
import os
import sys

from zenml import constants
from zenml.entrypoints.base_entrypoint_configuration import (
    ENTRYPOINT_CONFIG_SOURCE_OPTION,
    BaseEntrypointConfiguration,
)
from zenml.utils import source_utils


def _setup_logging() -> None:
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger().setLevel(logging.INFO)


def main() -> None:
    """Runs the entrypoint configuration given by the command line arguments."""
    _setup_logging()

    # Make sure this entrypoint does not run an entire pipeline when
    # importing user modules. This could happen if the `pipeline.run()` call
    # is not wrapped in a function or an `if __name__== "__main__":` check)
    constants.SHOULD_PREVENT_PIPELINE_EXECUTION = True

    # Read the source for the entrypoint configuration class from the command
    # line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(f"--{ENTRYPOINT_CONFIG_SOURCE_OPTION}", required=True)
    args, remaining_args = parser.parse_known_args()
    if isinstance(
        args.entrypoint_config_source, str
    ) and args.entrypoint_config_source.endswith(
        "DatabricksEntrypointConfiguration"
    ):
        source_utils.set_custom_source_root(source_root=os.getcwd())
    entrypoint_config_class = source_utils.load_and_validate_class(
        args.entrypoint_config_source,
        expected_class=BaseEntrypointConfiguration,
    )
    entrypoint_config = entrypoint_config_class(arguments=remaining_args)

    entrypoint_config.run()


if __name__ == "__main__":
    main()
