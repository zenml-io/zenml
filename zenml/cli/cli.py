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

# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. currentmodule:: ce_cli.cli
.. moduleauthor:: maiot GmbH <support@maiot.io>
"""

import logging
import os
import sys

import click

from zenml.cli.utils import pass_config

# set tensorflow logging level
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

LOGGING_LEVELS = {
    0: logging.NOTSET,
    1: logging.ERROR,
    2: logging.WARN,
    3: logging.INFO,
    4: logging.DEBUG,
}


@click.group()
@click.option("--verbose", "-v", default=0, count=True,
              help="Enable verbose output.")
@pass_config
def cli(info, verbose: int):
    """maiot ZenML"""
    info.load()
    if verbose > 0:
        logging.basicConfig(
            level=LOGGING_LEVELS[verbose]
            if verbose in LOGGING_LEVELS
            else logging.DEBUG
        )
        click.echo(
            click.style(
                f"Verbose logging is enabled. "
                f"(LEVEL={logging.getLogger().getEffectiveLevel()})",
                fg="yellow",
            )
        )
    else:
        logging.disable(sys.maxsize)
        logging.getLogger().disabled = True


if __name__ == '__main__':
    cli()
