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

import click

from zenml.cli.cli import cli, pass_config


@cli.group()
def analytics():
    """Analytics for opt-in and opt-out"""
    pass


@analytics.command('opt-in',
                   context_settings=dict(ignore_unknown_options=True))
@pass_config
def opt_in(info):
    """Opt-in to analytics"""
    info.set_analytics_opt_in(True)
    click.echo('Opted in to analytics.')


@analytics.command('opt-out',
                   context_settings=dict(ignore_unknown_options=True))
@pass_config
def opt_out(info):
    """Opt-out of analytics"""
    info.set_analytics_opt_in(False)
    click.echo('Opted out of analytics.')
