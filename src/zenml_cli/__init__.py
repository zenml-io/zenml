#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Core CLI functionality."""

import sys
import logging
from contextvars import ContextVar
import click
from typing import Optional

# Global variable to store original stdout for CLI clean output
_original_stdout = ContextVar("original_stdout", default=sys.stdout)


def reroute_stdout() -> None:
    """Reroute logging to stderr for CLI commands.

    This function redirects sys.stdout to sys.stderr so that all logging
    output goes to stderr, while preserving the original stdout for clean
    output that can be piped.
    """
    original_stdout = sys.stdout
    modified_handlers = []  # Track which handlers we actually modify

    # Store the original stdout for clean_output to use later
    _original_stdout.set(original_stdout)

    # Reroute stdout to stderr
    sys.stdout = sys.stderr

    # Handle existing root logger handlers that hold references to original stdout
    for handler in logging.root.handlers:
        if (
            isinstance(handler, logging.StreamHandler)
            and handler.stream is original_stdout
        ):  # Use 'is' for exact match
            handler.stream = sys.stderr
            modified_handlers.append(handler)  # Track this modification

    # Handle ALL existing individual logger handlers that hold references to original stdout
    for _, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
            for handler in logger.handlers:
                if (
                    isinstance(handler, logging.StreamHandler)
                    and handler.stream is original_stdout
                ):
                    handler.setStream(sys.stderr)
                    modified_handlers.append(handler)



def clean_output(text: str) -> None:
    """Output text to stdout for clean piping, bypassing stderr rerouting.

    This function ensures that specific output goes to the original stdout
    even when the CLI has rerouted stdout to stderr. This is useful for
    outputting data that should be pipeable (like JSON, CSV, YAML) while
    keeping logs and status messages in stderr.

    Args:
        text: Text to output to stdout.
    """
    original_stdout = _original_stdout.get()

    original_stdout.write(text)
    if not text.endswith("\n"):
        original_stdout.write("\n")
    original_stdout.flush()

# Only import 
reroute_stdout()

# Import the cli only after rerouting stdout
from zenml.cli.cli import cli
