#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from absl import logging as absl_logging

from zenml.enums import LoggingLevels

from zenml.constants import (  # isort: skip
    ABSL_LOGGING_VERBOSITY,
    APP_NAME,
)

FORMATTING_STRING = "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
FORMATTER = logging.Formatter(FORMATTING_STRING)
LOG_FILE = f"{APP_NAME}_logs.log"


def get_logging_level() -> LoggingLevels:
    """Get logging level from the config"""
    # GC also needs logging so we need to import locally.
    # from zenml.config.global_config import GlobalConfig

    # return GlobalConfig().logging_verbosity
    return LoggingLevels.INFO


def set_root_verbosity():
    """Set the root verbosity."""
    level = get_logging_level()
    if level != LoggingLevels.NOTSET:
        logging.basicConfig(level=level.value)
        get_logger(__name__).debug(
            f"Logging set to level: " f"{logging.getLevelName(level.value)}"
        )
    else:
        logging.disable(sys.maxsize)
        logging.getLogger().disabled = True
        get_logger(__name__).debug("Logging NOTSET")


def get_console_handler() -> Any:
    """Get console handler for logging."""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler() -> Any:
    """Return a file handler for logging."""
    file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight")
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name) -> Any:
    """Main function to get logger name,.

    Args:
      logger_name: Name of logger to initialize.

    Returns:
        A logger object.

    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(get_logging_level().value)
    logger.addHandler(get_console_handler())

    # TODO: [LOW] Add a file handler for persistent handling
    # logger.addHandler(get_file_handler())
    # with this pattern, it's rarely necessary to propagate the error up to
    # parent
    logger.propagate = False
    return logger


def init_logging():
    """Initialize logging with default levels."""
    # Mute tensorflow cuda warnings
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    logging.basicConfig(format=FORMATTING_STRING)
    set_root_verbosity()

    # set absl logging
    absl_logging.set_verbosity(ABSL_LOGGING_VERBOSITY)
