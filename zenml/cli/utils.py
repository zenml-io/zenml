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
from dateutil import tz

from zenml.repo import Repository, GlobalConfig

pass_config = click.make_pass_decorator(GlobalConfig, ensure=True)

pass_repo = click.make_pass_decorator(Repository, ensure=True)


def title(text):
    """
    Args:
        text:
    """
    click.echo(click.style(text.upper(), fg='cyan', bold=True, underline=True))


def confirmation(text, *args, **kwargs):
    """
    Args:
        text:
        *args:
        **kwargs:
    """
    return click.confirm(click.style(text, fg='yellow'), *args,
                         **kwargs)


def question(text, *args, **kwargs):
    """
    Args:
        text:
        *args:
        **kwargs:
    """
    return click.prompt(text=text, *args, **kwargs)


def declare(text):
    """
    Args:
        text:
    """
    click.echo(click.style(text, fg='green'))


def notice(text):
    """
    Args:
        text:
    """
    click.echo(click.style(text, fg='cyan'))


def error(text):
    """
    Args:
        text:
    """
    raise click.ClickException(message=click.style(text, fg='red', bold=True))


def warning(text):
    """
    Args:
        text:
    """
    click.echo(click.style(text, fg='yellow', bold=True))


def pretty_print(obj):
    """
    Args:
        obj:
    """
    click.echo(str(obj))


def format_date(dt, format='%Y-%m-%d %H:%M:%S'):
    """
    Args:
        dt:
        format:
    """
    if dt is None:
        return ''
    local_zone = tz.tzlocal()
    # make sure this is UTC
    dt = dt.replace(tzinfo=tz.tzutc())
    local_time = dt.astimezone(local_zone)
    return local_time.strftime(format)


def format_timedelta(td):
    """
    Args:
        td:
    """
    if td is None:
        return ''
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))


def parse_unknown_options(args):
    """
    Args:
        args:
    """
    warning_message = 'Please provide args with a proper ' \
                      'identifier as the key and the following structure: ' \
                      '--custom_argument="value"'

    assert all(a.startswith('--') for a in args), warning_message
    assert all(len(a.split('=')) == 2 for a in args), warning_message

    p_args = [a.lstrip('--').split('=') for a in args]

    assert all(k.isidentifier() for k, _ in p_args), warning_message

    r_args = {k: v for k, v in p_args}
    assert len(p_args) == len(r_args), 'Replicated arguments!'

    return r_args
