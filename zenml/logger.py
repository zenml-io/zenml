#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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

from absl import logging as absl_logging

from zenml.constants import ZENML_LOGGING_VERBOSITY, APP_NAME, \
    ABSL_LOGGING_VERBOSITY

# Mute tensorflow cuda warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

LOGGING_LEVELS = {
    0: logging.NOTSET,
    1: logging.ERROR,
    2: logging.WARN,
    3: logging.INFO,
    4: logging.DEBUG,
}

FORMATTING_STRING = "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
FORMATTER = logging.Formatter(FORMATTING_STRING)
LOG_FILE = f'{APP_NAME}_logs.log'


def resolve_logging_level():
    if ZENML_LOGGING_VERBOSITY > 0:
        level = LOGGING_LEVELS[ZENML_LOGGING_VERBOSITY] \
            if ZENML_LOGGING_VERBOSITY in LOGGING_LEVELS else logging.DEBUG
    else:
        level = logging.NOTSET
    return level


def set_root_verbosity():
    level = resolve_logging_level()
    if level > logging.NOTSET:
        logging.basicConfig(level=level)
        get_logger(__name__).debug(f'Logging set to level: '
                                   f'{logging.getLevelName(level)}')
    else:
        logging.disable(sys.maxsize)
        logging.getLogger().disabled = True
        get_logger(__name__).debug('Logging NOTSET')


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler():
    file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(resolve_logging_level())
    logger.addHandler(get_console_handler())

    # TODO: [LOW] Add a file handler for persistent handling
    # logger.addHandler(get_file_handler())
    # with this pattern, it's rarely necessary to propagate the error up to
    # parent
    logger.propagate = False
    return logger


def init_logging():
    logging.basicConfig(format=FORMATTING_STRING)
    set_root_verbosity()

    # set absl logging
    absl_logging.set_verbosity(ABSL_LOGGING_VERBOSITY)
