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

import datetime
import os
import re
import shutil
from distutils.core import run_setup

from tfx.utils import io_utils


def prepare_sdist():
    """
    Refer to the README.md in the docs folder
    """
    dist_path = os.path.join(os.getcwd(), 'dist')

    if os.path.exists(dist_path) and os.path.isdir(dist_path):
        print('Removing {}'.format(dist_path))
        shutil.rmtree(dist_path)
    else:
        print('There is no dist folder.')

    # FOR THE BOPA
    run_setup('setup.py', script_args=['sdist'])
    req_path = os.path.join(dist_path, 'requirements.txt')
    io_utils.write_string_file(req_path, '')

    # FOR THE BEPA
    run_setup('setup.py', script_args=['sdist'])
    req_path = os.path.join(dist_path, 'requirements.txt')
    io_utils.write_string_file(req_path, '')


def generate_unique_name(base_name):
    """
    Args:
        base_name:
    """
    identifier = os.getenv('CI_COMMIT_SHORT_SHA', os.getenv('USER', 'local'))
    return re.sub(
        r'[^0-9a-zA-Z-]+',
        '-',
        '{pipeline_name}-{identifier}-{ts}'.format(
            pipeline_name=base_name,
            identifier=identifier,
            ts=int(datetime.datetime.timestamp(datetime.datetime.now()))
        ).lower()
    )


def sanitize_name_for_ai_platform(name: str):
    """
    Args:
        name (str):
    """
    return 'ce_' + name.replace('-', '_').lower()


def parse_yaml_beam_args(pipeline_args):
    """Converts yaml beam args to list of args TFX accepts

    Args:
        pipeline_args: dict specified in the config.yml

    Returns:
        list of strings, where each string is a beam argument
    """
    return ['--{}={}'.format(key, value) for key, value in
            pipeline_args.items()]
